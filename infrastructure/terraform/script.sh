for stage in \
  stages/01-network \
  stages/02-foundation \
  stages/03-platform \
  stages/04-data \
  stages/05-application-foundation \
  stages/06-ingress
do
  echo ""
  echo "========================================"
  echo "VALIDATING: $stage"
  echo "========================================"

  (
    cd "$stage" || exit 1

    terraform init -backend=false
    terraform validate
  )

  if [ $? -ne 0 ]; then
    echo "❌ FAILED: $stage"
    exit 1
  else
    echo "✅ PASSED: $stage"
  fi
done