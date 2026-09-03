data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)
  az_index = {
    for index, az in local.azs : az => index
  }
  nat_gateway_count = var.nat_gateway_mode == "one_per_az" ? var.az_count : 1
  nat_gateway_keys  = toset([for index in range(local.nat_gateway_count) : tostring(index)])
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-vpc" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-igw" })
}

resource "aws_subnet" "public" {
  for_each = local.az_index

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = cidrsubnet(var.vpc_cidr, 5, each.value)
  map_public_ip_on_launch = false

  tags = merge(var.common_tags, {
    Name                     = "${var.name_prefix}-public-${each.key}"
    "kubernetes.io/role/elb" = "1"
  })
}

resource "aws_subnet" "private_app" {
  for_each = local.az_index

  vpc_id            = aws_vpc.this.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(var.vpc_cidr, 5, var.az_count + each.value)

  tags = merge(var.common_tags, {
    Name                              = "${var.name_prefix}-private-app-${each.key}"
    "kubernetes.io/role/internal-elb" = "1"
  })
}

resource "aws_subnet" "private_data" {
  for_each = local.az_index

  vpc_id            = aws_vpc.this.id
  availability_zone = each.key
  cidr_block        = cidrsubnet(var.vpc_cidr, 5, 2 * var.az_count + each.value)

  tags = merge(var.common_tags, {
    Name = "${var.name_prefix}-private-data-${each.key}"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-public" })
}

resource "aws_route_table_association" "public" {
  for_each       = local.az_index
  route_table_id = aws_route_table.public.id
  subnet_id      = aws_subnet.public[each.key].id
}

resource "aws_eip" "nat" {
  for_each = local.nat_gateway_keys
  domain   = "vpc"

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-nat-eip-${each.key}" })
}

resource "aws_nat_gateway" "this" {
  for_each = local.nat_gateway_keys

  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[local.azs[tonumber(each.key)]].id
  depends_on    = [aws_internet_gateway.this]

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-nat-${each.key}" })
}

resource "aws_route_table" "private_app" {
  for_each = local.az_index
  vpc_id   = aws_vpc.this.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.this[var.nat_gateway_mode == "one_per_az" ? tostring(each.value) : "0"].id
  }

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-private-app-${each.key}" })
}

resource "aws_route_table_association" "private_app" {
  for_each       = local.az_index
  route_table_id = aws_route_table.private_app[each.key].id
  subnet_id      = aws_subnet.private_app[each.key].id
}

resource "aws_route_table" "private_data" {
  for_each = local.az_index
  vpc_id   = aws_vpc.this.id

  tags = merge(var.common_tags, { Name = "${var.name_prefix}-private-data-${each.key}" })
}

resource "aws_route_table_association" "private_data" {
  for_each       = local.az_index
  route_table_id = aws_route_table.private_data[each.key].id
  subnet_id      = aws_subnet.private_data[each.key].id
}
