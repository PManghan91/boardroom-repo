"""Unit tests for sanitization utilities.

Tests input validation, sanitization functions, and security patterns
without requiring external dependencies.
"""

import pytest
from unittest.mock import patch

from app.utils.sanitization import (
    sanitize_string,
    sanitize_email,
    sanitize_dict,
    sanitize_list,
    validate_password_strength,
    sanitize_filename,
    sanitize_sql_like_pattern,
    validate_uuid_string,
    sanitize_json_data,
    validate_ip_address,
    sanitize_url,
    validate_content_type,
    sanitize_header_value
)


@pytest.mark.unit
class TestSanitizeString:
    """Test string sanitization function."""
    
    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        result = sanitize_string("Hello World")
        assert result == "Hello World"
    
    def test_sanitize_string_html_escape(self):
        """Test HTML character escaping."""
        result = sanitize_string("<script>alert('xss')</script>")
        assert "&lt;script&gt;" in result
        assert "&lt;/script&gt;" in result
        assert "<script>" not in result
    
    def test_sanitize_string_remove_script_tags(self):
        """Test script tag removal after escaping."""
        malicious = "<script>alert('xss')</script>Hello"
        result = sanitize_string(malicious)
        assert "script" not in result.lower()
        assert "Hello" in result
    
    def test_sanitize_string_remove_null_bytes(self):
        """Test null byte removal."""
        result = sanitize_string("Hello\x00World")
        assert result == "Hello World"
        assert "\x00" not in result
    
    def test_sanitize_string_non_string_input(self):
        """Test conversion of non-string input."""
        assert sanitize_string(123) == "123"
        assert sanitize_string(None) == "None"
        assert sanitize_string([1, 2, 3]) == "[1, 2, 3]"
    
    def test_sanitize_string_complex_html(self):
        """Test complex HTML sanitization."""
        html_input = '<div onclick="alert(\'xss\')">Content</div>'
        result = sanitize_string(html_input)
        assert "&lt;div" in result
        assert "onclick" in result
        assert "alert" in result
        assert "<div" not in result


@pytest.mark.unit
class TestSanitizeEmail:
    """Test email sanitization function."""
    
    def test_sanitize_email_valid(self):
        """Test valid email sanitization."""
        email = "test@example.com"
        result = sanitize_email(email)
        assert result == "test@example.com"
    
    def test_sanitize_email_uppercase(self):
        """Test email case normalization."""
        email = "TEST@EXAMPLE.COM"
        result = sanitize_email(email)
        assert result == "test@example.com"
    
    def test_sanitize_email_invalid_format(self):
        """Test invalid email format rejection."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test@.com",
            "test..test@example.com",
            "test@example",
            ""
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format"):
                sanitize_email(email)
    
    def test_sanitize_email_with_html(self):
        """Test email with HTML characters."""
        email = "test+tag@example.com"
        result = sanitize_email(email)
        assert result == "test+tag@example.com"
    
    def test_sanitize_email_malicious_input(self):
        """Test email with malicious content."""
        with pytest.raises(ValueError, match="Invalid email format"):
            sanitize_email("<script>@example.com")


@pytest.mark.unit
class TestSanitizeDict:
    """Test dictionary sanitization function."""
    
    def test_sanitize_dict_simple(self):
        """Test simple dictionary sanitization."""
        data = {"key": "value", "number": 123}
        result = sanitize_dict(data)
        assert result["key"] == "value"
        assert result["number"] == 123
    
    def test_sanitize_dict_nested(self):
        """Test nested dictionary sanitization."""
        data = {
            "user": {
                "name": "<script>alert('xss')</script>",
                "age": 25
            },
            "settings": {
                "theme": "dark"
            }
        }
        result = sanitize_dict(data)
        assert "&lt;script&gt;" in result["user"]["name"]
        assert result["user"]["age"] == 25
        assert result["settings"]["theme"] == "dark"
    
    def test_sanitize_dict_with_lists(self):
        """Test dictionary with list values."""
        data = {
            "tags": ["<script>", "normal", 123],
            "meta": {"count": 1}
        }
        result = sanitize_dict(data)
        assert "&lt;script&gt;" in result["tags"][0]
        assert result["tags"][1] == "normal"
        assert result["tags"][2] == 123
        assert result["meta"]["count"] == 1


@pytest.mark.unit
class TestSanitizeList:
    """Test list sanitization function."""
    
    def test_sanitize_list_simple(self):
        """Test simple list sanitization."""
        data = ["hello", "world", 123]
        result = sanitize_list(data)
        assert result == ["hello", "world", 123]
    
    def test_sanitize_list_with_html(self):
        """Test list with HTML content."""
        data = ["<script>alert('xss')</script>", "normal", {"key": "<div>"}]
        result = sanitize_list(data)
        assert "&lt;script&gt;" in result[0]
        assert result[1] == "normal"
        assert "&lt;div&gt;" in result[2]["key"]
    
    def test_sanitize_list_nested(self):
        """Test nested list sanitization."""
        data = [
            ["<script>", "nested"],
            {"nested_dict": "<div>content</div>"},
            123
        ]
        result = sanitize_list(data)
        assert "&lt;script&gt;" in result[0][0]
        assert result[0][1] == "nested"
        assert "&lt;div&gt;" in result[1]["nested_dict"]
        assert result[2] == 123


@pytest.mark.unit
class TestValidatePasswordStrength:
    """Test password strength validation."""
    
    def test_validate_password_strength_valid(self):
        """Test valid strong passwords."""
        valid_passwords = [
            "Password123!",
            "ComplexP@ssw0rd",
            "MySecure#Pass1",
            "Str0ng$Password"
        ]
        
        for password in valid_passwords:
            assert validate_password_strength(password) is True
    
    def test_validate_password_strength_too_short(self):
        """Test password too short."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password_strength("P@ss1")
    
    def test_validate_password_strength_no_uppercase(self):
        """Test password without uppercase."""
        with pytest.raises(ValueError, match="uppercase letter"):
            validate_password_strength("password123!")
    
    def test_validate_password_strength_no_lowercase(self):
        """Test password without lowercase."""
        with pytest.raises(ValueError, match="lowercase letter"):
            validate_password_strength("PASSWORD123!")
    
    def test_validate_password_strength_no_number(self):
        """Test password without number."""
        with pytest.raises(ValueError, match="one number"):
            validate_password_strength("Password!")
    
    def test_validate_password_strength_no_special(self):
        """Test password without special character."""
        with pytest.raises(ValueError, match="special character"):
            validate_password_strength("Password123")


@pytest.mark.unit
class TestSanitizeFilename:
    """Test filename sanitization function."""
    
    def test_sanitize_filename_normal(self):
        """Test normal filename."""
        result = sanitize_filename("document.pdf")
        assert result == "document.pdf"
    
    def test_sanitize_filename_dangerous_chars(self):
        """Test filename with dangerous characters."""
        result = sanitize_filename("file<>:\"/\\|?*.txt")
        assert result == "file.txt"
    
    def test_sanitize_filename_path_traversal(self):
        """Test filename with path traversal attempts."""
        result = sanitize_filename("../../../etc/passwd")
        assert result == "etcpasswd"
        assert "../" not in result
    
    def test_sanitize_filename_null_bytes(self):
        """Test filename with null bytes."""
        result = sanitize_filename("file\x00name.txt")
        assert result == "filename.txt"
        assert "\x00" not in result
    
    def test_sanitize_filename_too_long(self):
        """Test very long filename."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".txt")


@pytest.mark.unit
class TestSanitizeSqlLikePattern:
    """Test SQL LIKE pattern sanitization."""
    
    def test_sanitize_sql_like_pattern_normal(self):
        """Test normal pattern."""
        result = sanitize_sql_like_pattern("search_term")
        assert result == "search_term"
    
    def test_sanitize_sql_like_pattern_special_chars(self):
        """Test pattern with SQL special characters."""
        result = sanitize_sql_like_pattern("search%_[term")
        assert result == "search\\%\\_\\[term"
        assert "%" not in result.replace("\\%", "")
        assert "_" not in result.replace("\\_", "")
    
    def test_sanitize_sql_like_pattern_backslash(self):
        """Test pattern with backslashes."""
        result = sanitize_sql_like_pattern("search\\term")
        assert result == "search\\\\term"


@pytest.mark.unit
class TestValidateUuidString:
    """Test UUID string validation."""
    
    def test_validate_uuid_string_valid(self):
        """Test valid UUID strings."""
        valid_uuids = [
            "123e4567-e89b-12d3-a456-426614174000",
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        ]
        
        for uuid_str in valid_uuids:
            result = validate_uuid_string(uuid_str)
            assert result == uuid_str
    
    def test_validate_uuid_string_invalid(self):
        """Test invalid UUID strings."""
        invalid_uuids = [
            "not-a-uuid",
            "123e4567-e89b-12d3-a456",
            "123e4567-e89b-12d3-a456-426614174000-extra",
            "",
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        ]
        
        for uuid_str in invalid_uuids:
            with pytest.raises(ValueError, match="Invalid UUID format"):
                validate_uuid_string(uuid_str)


@pytest.mark.unit
class TestSanitizeJsonData:
    """Test JSON data sanitization with depth protection."""
    
    def test_sanitize_json_data_simple(self):
        """Test simple JSON data sanitization."""
        data = {"message": "<script>alert('xss')</script>", "count": 5}
        result = sanitize_json_data(data)
        assert "&lt;script&gt;" in result["message"]
        assert result["count"] == 5
    
    def test_sanitize_json_data_nested(self):
        """Test nested JSON data sanitization."""
        data = {
            "level1": {
                "level2": {
                    "message": "<script>",
                    "safe": "content"
                }
            }
        }
        result = sanitize_json_data(data)
        assert "&lt;script&gt;" in result["level1"]["level2"]["message"]
        assert result["level1"]["level2"]["safe"] == "content"
    
    def test_sanitize_json_data_max_depth(self):
        """Test maximum depth protection."""
        # Create deeply nested data
        data = {"level": {}}
        current = data["level"]
        for i in range(15):  # Exceed default max depth of 10
            current["next"] = {}
            current = current["next"]
        
        with pytest.raises(ValueError, match="exceeds maximum depth"):
            sanitize_json_data(data)
    
    def test_sanitize_json_data_large_dict(self):
        """Test large dictionary protection."""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(1001)}
        
        with pytest.raises(ValueError, match="Dictionary too large"):
            sanitize_json_data(large_dict)
    
    def test_sanitize_json_data_large_list(self):
        """Test large list protection."""
        large_list = [f"item_{i}" for i in range(1001)]
        
        with pytest.raises(ValueError, match="List too large"):
            sanitize_json_data(large_list)


@pytest.mark.unit
class TestValidateIpAddress:
    """Test IP address validation."""
    
    def test_validate_ip_address_ipv4(self):
        """Test valid IPv4 addresses."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "127.0.0.1",
            "8.8.8.8",
            "255.255.255.255"
        ]
        
        for ip in valid_ips:
            result = validate_ip_address(ip)
            assert result == ip
    
    def test_validate_ip_address_ipv6(self):
        """Test valid IPv6 addresses."""
        valid_ips = [
            "::1",
            "2001:db8::1",
            "fe80::1%lo0",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        ]
        
        for ip in valid_ips:
            result = validate_ip_address(ip)
            assert result == ip
    
    def test_validate_ip_address_invalid(self):
        """Test invalid IP addresses."""
        invalid_ips = [
            "256.256.256.256",
            "192.168.1",
            "not.an.ip.address",
            "192.168.1.1.1",
            ""
        ]
        
        for ip in invalid_ips:
            with pytest.raises(ValueError, match="Invalid IP address format"):
                validate_ip_address(ip)


@pytest.mark.unit
class TestSanitizeUrl:
    """Test URL sanitization function."""
    
    def test_sanitize_url_valid(self):
        """Test valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://test.org/path",
            "ftp://files.example.com/file.txt",
            "https://api.example.com/v1/users?id=123"
        ]
        
        for url in valid_urls:
            result = sanitize_url(url)
            assert result == url
    
    def test_sanitize_url_dangerous_schemes(self):
        """Test dangerous URL schemes."""
        dangerous_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "file:///etc/passwd"
        ]
        
        for url in dangerous_urls:
            with pytest.raises(ValueError, match="dangerous protocol"):
                sanitize_url(url)
    
    def test_sanitize_url_invalid_scheme(self):
        """Test invalid URL schemes."""
        with pytest.raises(ValueError, match="URL scheme must be one of"):
            sanitize_url("custom://example.com")
    
    def test_sanitize_url_malformed(self):
        """Test malformed URLs."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            sanitize_url("not a url")


@pytest.mark.unit
class TestValidateContentType:
    """Test content type validation."""
    
    def test_validate_content_type_valid(self):
        """Test valid content types."""
        valid_types = [
            "application/json",
            "text/plain",
            "image/jpeg",
            "application/pdf"
        ]
        
        for content_type in valid_types:
            result = validate_content_type(content_type)
            assert result == content_type
    
    def test_validate_content_type_with_parameters(self):
        """Test content type with parameters."""
        content_type = "application/json; charset=utf-8"
        result = validate_content_type(content_type)
        assert result == content_type
    
    def test_validate_content_type_invalid(self):
        """Test invalid content types."""
        with pytest.raises(ValueError, match="Content type not allowed"):
            validate_content_type("application/x-dangerous")


@pytest.mark.unit
class TestSanitizeHeaderValue:
    """Test HTTP header value sanitization."""
    
    def test_sanitize_header_value_normal(self):
        """Test normal header value."""
        result = sanitize_header_value("Bearer token123")
        assert result == "Bearer token123"
    
    def test_sanitize_header_value_remove_newlines(self):
        """Test header injection prevention."""
        malicious = "Bearer token\r\nX-Injected: malicious"
        result = sanitize_header_value(malicious)
        assert "\r" not in result
        assert "\n" not in result
        assert result == "Bearer tokenX-Injected: malicious"
    
    def test_sanitize_header_value_remove_null_bytes(self):
        """Test null byte removal."""
        result = sanitize_header_value("Bearer\x00token")
        assert result == "Bearertoken"
        assert "\x00" not in result
    
    def test_sanitize_header_value_length_limit(self):
        """Test header length limit."""
        long_value = "a" * 10000
        result = sanitize_header_value(long_value)
        assert len(result) == 8192


@pytest.mark.unit
class TestSanitizationIntegration:
    """Integration tests for sanitization utilities."""
    
    def test_comprehensive_sanitization(self):
        """Test comprehensive data sanitization."""
        malicious_data = {
            "user": {
                "name": "<script>alert('xss')</script>",
                "email": "test@example.com",
                "preferences": [
                    "<iframe src='javascript:alert(1)'>",
                    "normal_preference",
                    {"setting": "<div onclick='evil()'>content</div>"}
                ]
            },
            "session": {
                "id": "session-123",
                "data": "Safe\x00Content"
            }
        }
        
        result = sanitize_dict(malicious_data)
        
        # Verify HTML is escaped
        assert "&lt;script&gt;" in result["user"]["name"]
        assert "<script>" not in result["user"]["name"]
        
        # Verify nested sanitization
        assert "&lt;iframe" in result["user"]["preferences"][0]
        assert result["user"]["preferences"][1] == "normal_preference"
        assert "&lt;div" in result["user"]["preferences"][2]["setting"]
        
        # Verify null bytes removed
        assert "\x00" not in result["session"]["data"]
        assert result["session"]["data"] == "SafeContent"
        
        # Verify safe content unchanged
        assert result["user"]["email"] == "test@example.com"
        assert result["session"]["id"] == "session-123"