#!/usr/bin/env python
"""
ARTEF Setup Verification Script
Verifies that all prerequisites and configurations are correct before deployment.
"""

import os
import sys
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(message):
    print(f"{Colors.GREEN}âœ“ {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}âš  {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}âœ— {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}â„¹ {message}{Colors.END}")

def print_header(message):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print(f"{message}")
    print(f"{'='*70}{Colors.END}\n")

def check_python_version():
    """Check if Python version is 3.11+"""
    if sys.version_info < (3, 11):
        print_error(f"Python 3.11+ required. Found: {sys.version}")
        return False
    print_success(f"Python version: {sys.version.split()[0]}")
    return True

def check_file_exists(filepath, description, critical=True):
    """Check if a file exists"""
    if Path(filepath).exists():
        print_success(f"{description}: {filepath}")
        return True
    else:
        if critical:
            print_error(f"{description} missing: {filepath}")
        else:
            print_warning(f"{description} missing (optional): {filepath}")
        return not critical

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path(".env")
    if not env_path.exists():
        print_error(".env file not found. Copy .env.example to .env")
        return False
    
    print_success(".env file exists")
    
    with open(env_path) as f:
        env_content = f.read()
    
    required_vars = [
        ("SECRET_KEY", "SECRET_KEY="),
        ("DATABASE_URL", "DATABASE_URL="),
        ("JWT_PRIVATE_KEY_PATH", "JWT_PRIVATE_KEY_PATH="),
        ("JWT_PUBLIC_KEY_PATH", "JWT_PUBLIC_KEY_PATH="),
    ]
    
    all_found = True
    for var_name, var_pattern in required_vars:
        if var_pattern not in env_content:
            print_error(f"Missing {var_name} in .env")
            all_found = False
        else:
            for line in env_content.split('\n'):
                if line.startswith(var_pattern):
                    value = line.split('=', 1)[1].strip('"\'')
                    if not value or value.startswith('REPLACE_THIS') or value == '':
                        print_warning(f"{var_name} is not set in .env")
                    else:
                        print_success(f"{var_name} is configured")
                    break
    
    return all_found

def check_jwt_keys():
    """Check if JWT keys exist"""
    key_dir = Path("backend/app/core/keys")
    private_key = key_dir / "private_key.pem"
    public_key = key_dir / "public_key.pem"
    
    if not key_dir.exists():
        print_error(f"Keys directory not found: {key_dir}")
        print_info("Run: mkdir -p backend/app/core/keys")
        return False
    
    private_exists = check_file_exists(private_key, "JWT private key", critical=True)
    public_exists = check_file_exists(public_key, "JWT public key", critical=True)
    
    if private_exists and public_exists:
        with open(private_key) as f:
            private_content = f.read()
        
        if "demo" in private_content.lower() or len(private_content) < 1000:
            print_warning("Using demo JWT keys! Generate new keys for production!")
            print_info("Generate keys with:")
            print_info("  openssl genrsa -out backend/app/core/keys/private_key.pem 2048")
            print_info("  openssl rsa -in backend/app/core/keys/private_key.pem -pubout -out backend/app/core/keys/public_key.pem")
        else:
            print_success("JWT keys configured")
    
    return private_exists and public_exists

def check_backend_dependencies():
    """Check if backend dependencies are installed"""
    try:
        import fastapi
        import sqlalchemy
        import pydantic
        print_success("Backend dependencies installed")
        return True
    except ImportError as e:
        print_error(f"Backend dependencies missing: {e}")
        print_info("Run: pip install -e .")
        return False

def check_frontend_dependencies():
    """Check if frontend dependencies are installed"""
    node_modules = Path("frontend/node_modules")
    if node_modules.exists():
        print_success("Frontend dependencies installed")
        return True
    else:
        print_error("Frontend node_modules not found")
        print_info("Run: cd frontend && npm install")
        return False

def check_docker():
    """Check if Docker is available (optional)"""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print_success(f"Docker available: {result.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print_warning("Docker not found (optional for development)")
    return False

def check_git_repo():
    """Check if .git exists and status"""
    git_dir = Path(".git")
    if git_dir.exists():
        print_success("Git repository initialized")
        
        gitignore = Path(".gitignore")
        if gitignore.exists():
            with open(gitignore) as f:
                content = f.read()
            
            critical_ignores = [".env", "*.pem", "*.key", "*.db"]
            missing_ignores = [pattern for pattern in critical_ignores if pattern not in content]
            
            if missing_ignores:
                print_warning(f"Ensure .gitignore includes: {', '.join(missing_ignores)}")
            else:
                print_success("Critical files properly gitignored")
        return True
    else:
        print_warning("Not a git repository")
        return False

def check_database_url():
    """Check database URL configuration"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    db_url = os.getenv("DATABASE_URL", "")
    
    if not db_url:
        print_error("DATABASE_URL not set in .env")
        return False
    
    if "sqlite" in db_url:
        print_warning("Using SQLite (development only)")
        print_info("For production, use PostgreSQL")
    elif "postgresql" in db_url:
        print_success("Using PostgreSQL database")
    else:
        print_warning(f"Unknown database: {db_url}")
    
    return True

def check_security_config():
    """Check security-related configurations"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    secret_key = os.getenv("SECRET_KEY", "")
    environment = os.getenv("ENVIRONMENT", "development")
    cors_origins = os.getenv("CORS_ORIGINS", "")
    
    issues = []
    
    if len(secret_key) < 32:
        issues.append("SECRET_KEY too short (minimum 32 characters)")
    
    if "your-secret-key" in secret_key.lower() or "change" in secret_key.lower():
        issues.append("SECRET_KEY appears to be default value")
    
    if environment == "production":
        if "*" in cors_origins:
            issues.append("CORS wildcard (*) not allowed in production")
        
        if "localhost" in cors_origins:
            issues.append("localhost in CORS_ORIGINS (production)")
    
    if issues:
        for issue in issues:
            print_error(f"Security issue: {issue}")
        return False
    else:
        print_success("Security configuration OK")
        return True

def main():
    """Main verification function"""
    print_header("ARTEF Setup Verification")
    print_info("Checking project configuration and dependencies...")
    
    checks = []
    
    print_header("1. Critical Requirements")
    checks.append(("Python Version", check_python_version()))
    checks.append((".env Configuration", check_env_file()))
    checks.append(("JWT Keys", check_jwt_keys()))
    checks.append(("Database Config", check_database_url()))
    
    print_header("2. Dependencies")
    checks.append(("Backend Dependencies", check_backend_dependencies()))
    checks.append(("Frontend Dependencies", check_frontend_dependencies()))
    
    print_header("3. Security Configuration")
    checks.append(("Security Settings", check_security_config()))
    checks.append(("Git Configuration", check_git_repo()))
    
    print_header("4. Optional Tools")
    checks.append(("Docker", check_docker()))
    
    print_header("Verification Summary")
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    critical_passed = sum(1 for _, result in checks[:4] if result)
    
    print(f"\nPassed: {passed}/{total} checks")
    print(f"Critical: {critical_passed}/4 checks")
    
    if critical_passed == 4:
        print_success("\nâœ“ All critical checks passed! Ready for development.")
        
        if passed == total:
            print_success("âœ“ All optional checks passed! Fully configured.")
            return 0
        else:
            print_warning("\nSome optional features not configured.")
            print_info("Review warnings above for optional improvements.")
            return 0
    else:
        print_error("\nâœ— Critical checks failed! Fix errors before proceeding.")
        print_info("\nRefer to SETUP.md for detailed setup instructions.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
