import re
import dns.resolver  # Requires the `dnspython` package
import socket

def validate_email(email: str) -> tuple[bool, str]:
    """
    Validate an email address using regex and DNS lookup.
    
    Args:
        email (str): The email address to validate.
        
    Returns:
        tuple[bool, str]: (is_valid, message) where is_valid is True if the email is valid,
                          and message provides details on the validation result or error.
    """
    # Step 1: Basic format validation using regex
    # Regex pattern for email validation (simplified but covers most cases)
    # - Local part: allows letters, numbers, and some special characters (e.g., .!#$%&'*+/=?^_`{|}~-)
    # - Domain part: allows letters, numbers, hyphens, and dots
    email_pattern = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    
    if not email:
        return False, "Email address cannot be empty."
    
    # Check length (RFC 5322 recommends max 254 characters for email addresses)
    if len(email) > 254:
        return False, "Email address is too long (max 254 characters)."
    
    # Check local part length (before the @) - max 64 characters per RFC 5321
    local_part = email.split('@')[0] if '@' in email else email
    if len(local_part) > 64:
        return False, "Local part of email (before @) is too long (max 64 characters)."
    
    # Apply regex pattern
    if not re.match(email_pattern, email):
        return False, "Invalid email format. Ensure it follows the pattern: user@domain.com."
    
    # Step 2: Split email into local part and domain
    try:
        local, domain = email.split('@')
    except ValueError:
        return False, "Email must contain exactly one '@' symbol."
    
    # Check domain part length (max 255 characters per RFC 5321)
    if len(domain) > 255:
        return False, "Domain part of email (after @) is too long (max 255 characters)."
    
    # Step 3: Validate domain using DNS lookup
    try:
        # Check for MX records (Mail Exchange records)
        mx_records = dns.resolver.resolve(domain, 'MX')
        if not mx_records:
            return False, f"No MX records found for domain '{domain}'. This domain may not be able to receive emails."
        
        # Optionally, check for A record as a fallback (some domains might not have MX but can still receive email)
        try:
            dns.resolver.resolve(domain, 'A')
        except dns.resolver.NoAnswer:
            pass  # A record check is optional; MX is the primary indicator
        
    except dns.resolver.NXDOMAIN:
        return False, f"Domain '{domain}' does not exist (NXDOMAIN)."
    except dns.resolver.NoAnswer:
        return False, f"No DNS records found for domain '{domain}'."
    except dns.resolver.LifetimeTimeout:
        return False, f"DNS lookup timed out for domain '{domain}'. Unable to validate."
    except Exception as e:
        return False, f"Error during DNS lookup for domain '{domain}': {str(e)}"
    
    # Step 4: Additional checks (optional)
    # Check for consecutive dots in local part or domain
    if '..' in local or '..' in domain:
        return False, "Email address cannot contain consecutive dots in local part or domain."
    
    # Check if domain starts or ends with a hyphen
    if domain.startswith('-') or domain.endswith('-'):
        return False, "Domain cannot start or end with a hyphen."
    
    # Step 5: If all checks pass, the email is considered valid
    return True, "Email address is valid."

def main():
    # Test cases
    test_emails = [
        "steve@findlayroofing.com",  # Valid email (assuming domain exists)
        "sfindlay@findlayroofing.com",  # Valid email (assuming domain exists)
        "financing@roofroof.com",    # Valid email (known to exist)
        "invalid.email@nonexistentdomain12345.com",  # Invalid domain
        "no-at-sign.com",            # Missing @ symbol
        "user@domain..com",          # Consecutive dots in domain
        "user@-domain.com",          # Domain starts with hyphen
        "a" * 65 + "@domain.com",    # Local part too long
        "user@" + "a" * 256 + ".com",  # Domain part too long
        "",                          # Empty string
        "invalid@domain",            # Missing top-level domain
    ]
    
    print("Testing email validation:\n")
    for email in test_emails:
        is_valid, message = validate_email(email)
        print(f"Email: {email}")
        print(f"Valid: {is_valid}")
        print(f"Message: {message}\n")

if __name__ == "__main__":
    main()