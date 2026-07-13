## ADDED Requirements

### Requirement: HTTPS redirection
Nginx SHALL redirect all HTTP traffic to HTTPS.

#### Scenario: HTTP redirected to HTTPS
- **WHEN** a client sends a request via HTTP on port 80
- **THEN** nginx SHALL respond with a 301 redirect to the same URL using HTTPS

### Requirement: Security headers
Nginx SHALL include security headers in all responses.

#### Scenario: Security headers present
- **WHEN** nginx serves any response
- **THEN** the response SHALL include: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`
- **AND** SHALL include: `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- **AND** SHALL include: `Content-Security-Policy` restricting script sources to self and trusted CDNs

### Requirement: Rate limiting
Nginx SHALL rate-limit requests to sensitive endpoints.

#### Scenario: Auth rate limit enforced
- **WHEN** a client exceeds 10 requests per minute to `/auth/`
- **THEN** nginx SHALL respond with 429 Too Many Requests

#### Scenario: API rate limit enforced
- **WHEN** a client exceeds 100 requests per minute to `/api/`
- **THEN** nginx SHALL respond with 429 Too Many Requests

#### Scenario: Rate limit by IP
- **WHEN** rate limiting is triggered
- **THEN** the limit SHALL be applied per client IP address

### Requirement: Request body size limit
Nginx SHALL enforce a maximum request body size.

#### Scenario: Large body rejected
- **WHEN** a client sends a request with body larger than 10MB
- **THEN** nginx SHALL respond with 413 Request Entity Too Large

### Requirement: HTTPS certificate support
Nginx SHALL be configured to support HTTPS with Let's Encrypt certificates.

#### Scenario: HTTPS configured
- **WHEN** nginx starts
- **THEN** it SHALL listen on port 443 with SSL certificate and key paths defined
- **AND** SHALL use TLS 1.2 or 1.3 only (no TLS 1.0/1.1)
- **AND** SHALL use secure ciphers (`ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:...`)
