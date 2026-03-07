# Bug Report - Eknal Link Application

**Date:** March 7, 2026  
**File Analyzed:** `app.py`

---

## Critical Bugs

### 1. Syntax Error - Line 159
**Severity:** CRITICAL  
**Location:** `edit_link()` function  
**Issue:** Trailing backslash at end of return statement causes syntax error

```python
# Current (BROKEN):
return render_template("edit_link.html", link=link)\

# Fix:
return render_template("edit_link.html", link=link)
```

**Impact:** Application will not run

---

## High Priority Bugs

### 2. Missing File Upload Validation - Line 192
**Severity:** HIGH  
**Location:** `add_file()` function  
**Issue:** No check if file exists or has filename before validation

```python
# Current (VULNERABLE):
file = request.files["file"]
if not allowed_file(file.filename):

# Fix:
file = request.files.get("file")
if not file or file.filename == '' or not allowed_file(file.filename):
    flash("No file selected or invalid file type", "danger")
    return redirect(url_for("add_file"))
```

**Impact:** Can cause AttributeError if no file is uploaded

---

### 3. Race Condition in File Deletion - Line 237
**Severity:** HIGH  
**Location:** `delete_file()` function  
**Issue:** File deleted from disk before database commit

```python
# Current (RISKY):
if os.path.exists(path):
    os.remove(path)
db.session.delete(f)
db.session.commit()

# Fix:
db.session.delete(f)
db.session.commit()
if os.path.exists(path):
    os.remove(path)
```

**Impact:** If commit fails, file is deleted but DB record remains

---

## Security Vulnerabilities

### 4. Hardcoded Admin Credentials - Lines 44-45
**Severity:** CRITICAL SECURITY RISK  
**Location:** Global constants  
**Issue:** Plain text credentials in source code

```python
# Current (INSECURE):
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Fix: Use environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
```

**Impact:** Anyone with code access has admin credentials

---

### 5. Hardcoded Secret Key - Line 31
**Severity:** HIGH SECURITY RISK  
**Location:** Flask configuration  
**Issue:** Weak, hardcoded secret key

```python
# Current (INSECURE):
app.config["SECRET_KEY"] = "super-secret-key"

# Fix:
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24).hex())
```

**Impact:** Session hijacking, CSRF attacks possible

---

## Code Quality Issues

### 6. Duplicate Import - Line 7
**Severity:** LOW  
**Location:** Top of file  
**Issue:** `import os` appears twice (lines 1 and 7)

```python
# Remove duplicate on line 7
```

**Impact:** Code redundancy, no functional impact

---

### 7. Missing Email Validation - Line 367
**Severity:** MEDIUM  
**Location:** `request_edit()` function  
**Issue:** No email format validation before database query

```python
# Add validation:
import re
email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
if not re.match(email_pattern, email):
    flash("Invalid email format", "danger")
    return redirect(url_for("request_edit"))
```

**Impact:** Poor user experience, potential injection risks

---

### 8. Debug Code Left in Production - Lines 367-376
**Severity:** LOW  
**Location:** `request_edit()` function  
**Issue:** Performance timing code should be removed

```python
# Remove these lines:
from time import perf_counter
start=perf_counter()
# ... timing statements
print(f"{duration:.4f} seconds 367")
```

**Impact:** Console clutter, minor performance overhead

---

## Summary

- **Critical Issues:** 2 (syntax error, hardcoded credentials)
- **High Priority:** 2 (file validation, race condition)
- **Security Risks:** 2 (credentials, secret key)
- **Code Quality:** 3 (duplicate import, validation, debug code)

**Recommended Action:** Fix critical issues immediately before deployment.
