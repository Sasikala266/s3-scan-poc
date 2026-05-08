# Design Decisions & Future Enhancements – S3 File Scan POC

This document captures the key technical and architectural decisions made while implementing the S3 File Scan POC, along with identified improvement areas and future enhancement options.

The intention is to explain **why specific choices were made** and how the solution can evolve into a production‑ready implementation.

---

## Key Design Decisions

### 1. Serverless Architecture
**Decision:**  
Use AWS managed serverless services (S3, API Gateway, Lambda).

**Rationale:**
- No infrastructure management or scaling concerns
- Pay‑per‑use cost model
- Fast iteration and deployment
- Ideal for POCs and lightweight workloads

This approach keeps operational overhead minimal and aligns with modern cloud-native patterns.

---

### 2. Static Frontend Hosted on Amazon S3
**Decision:**  
Host the UI as a static website in Amazon S3.

**Rationale:**
- Simple and cost‑effective
- No backend maintenance
- Easy integration with API Gateway
- Works well for lightweight interactive UIs

The frontend is intentionally kept **dumb** — it performs no logic beyond sending user input to the backend.

---

### 3. REST API Gateway (Not HTTP API)
**Decision:**  
Use **Amazon API Gateway REST API** instead of HTTP API.

**Rationale:**
- Explicit stage management (`/prod`)
- Clear resource‑based routing (`/scan`)
- Better visibility for learning and debugging
- Familiar enterprise pattern

Although HTTP APIs are cheaper and simpler, REST API was chosen to make routing, stages, and CORS behavior more explicit for demonstration and learning purposes.

---

### 4. Backend‑Driven File Discovery
**Decision:**  
Accept **only file name input** from the UI and handle all discovery logic in Lambda.

**Rationale:**
- UI should not know storage layout
- Prevents exposing internal bucket structure
- Centralizes validation and search logic
- Enables future backend enhancements without UI changes

This improves security, maintainability, and extensibility.

---

### 5. Prefix‑Based S3 Organization
**Decision:**  
Organize files in S3 using logical prefixes based on file type (`csv/`, `json/`, `xml/`, `html/`).

**Rationale:**
- Simple and scalable search strategy
- Reduces unnecessary lookups
- Easy to extend with new file types
- Clear separation of data categories

---

### 6. Input Validation in Lambda
**Decision:**  
Perform strict validation on `file_name` inside Lambda.

**Validations include:**
- Missing file name
- Missing extension
- Unsupported extension
- File not found

**Rationale:**
- Improves user experience
- Prevents unnecessary S3 calls
- Makes error handling predictable
- Keeps the UI simple

---

### 7. Dual Invocation Support (API + Direct Test)
**Decision:**  
Support both:
- API Gateway invocations
- Direct Lambda “Test Event” execution

**Rationale:**
- Simplifies development and debugging
- Enables local validation without frontend
- Improves maintainability for future testing frameworks

---

## Security Considerations

### Current State (POC)
- Public S3 access enabled to serve static UI
- Lambda uses minimal IAM permissions
- No credentials exposed to frontend

### Known Limitation
Public S3 access was enabled manually due to enterprise‑level S3 Block Public Access guardrails preventing Terraform‑based public policies.

This approach is acceptable **only for POC/demo purposes**.

---

## Future Enhancements

### 1. Replace Public S3 with CloudFront + OAC
**Description:**
- S3 remains private
- CloudFront serves UI
- Origin Access Control (OAC) enforces secure access

**Benefits:**
- Aligns with AWS security best practices
- Removes public S3 policies
- Improves performance and caching
- Terraform‑friendly in enterprise accounts

---

### 2. Authentication & Authorization
**Options:**
- Amazon Cognito
- IAM authentication
- API keys (for controlled usage)

**Benefits:**
- Restrict access to the scan API
- Enable multi‑user scenarios
- Add audit traceability

---

### 3. Enhanced Search Capability
Potential enhancements:
- Partial or fuzzy filename matching
- Case‑insensitive search
- Return multiple matches instead of single file
- Search across configurable buckets

---

### 4. Metadata & File Insights
Lambda can be extended to:
- Return file size
- Display last modified timestamp
- Validate file schema (CSV/JSON)
- Perform content scanning or rule checks

---

### 5. UI Enhancements
Possible frontend improvements:
- Dropdown of recently discovered files
- Auto‑suggest based on prefix
- Better formatted response display
- Loading indicators and tooltips

---

### 6. Scalability & Observability
- Add CloudWatch structured logging
- Track search latency metrics
- Integrate AWS X‑Ray
- Add alarms for error rate

---

## Migration to Production (High‑Level Steps)
1. Replace public S3 with CloudFront + OAC
2. Enable authentication
3. Add structured monitoring
4. Restrict IAM policies further
5. Implement CI/CD promotion controls
6. Add automated testing

---

## Conclusion

This POC intentionally prioritizes **clarity, learning, and speed** over full production hardening.

The current design demonstrates:
- Clean separation of concerns
- Strong serverless fundamentals
- Secure backend‑driven logic
- Clear upgrade path to enterprise‑grade architecture

With minimal additional effort, the solution can confidently evolve into a production‑ready system.