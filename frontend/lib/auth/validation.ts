const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export interface CredentialsErrors {
  email?: string;
  password?: string;
}

export function validateCredentials(
  email: string,
  password: string,
): CredentialsErrors {
  const errors: CredentialsErrors = {};
  if (!EMAIL_PATTERN.test(email.trim()))
    errors.email = "Enter a valid email address.";
  if (!password) errors.password = "Enter your password.";
  if (password.length > 128)
    errors.password = "Password must be at most 128 characters.";
  return errors;
}

export function validateRegistration(
  email: string,
  password: string,
  confirmation: string,
): CredentialsErrors & { confirmation?: string } {
  const errors: CredentialsErrors & { confirmation?: string } =
    validateCredentials(email, password);
  if (password.length < 12)
    errors.password = "Password must be at least 12 characters.";
  if (password !== confirmation)
    errors.confirmation = "Passwords do not match.";
  return errors;
}
