# Cloud Storage Service — Specification

## 1. Project Overview

**Objective:** Build a cloud file storage service using **FastAPI** and **RustFS**, with JWT-based authentication and support for a broad set of Amazon S3 API capabilities.

The service exposes a REST API that allows users to upload, download, organize, and manage their files. The solution consists of **two independent microservices**: an Authentication Service and a Cloud Service.

## 2. System Architecture

```text
                  +---------------------------+
                  | Client (Web / Mobile / CLI)|
                  +-------------+-------------+
                                |
                     HTTPS / REST API
                                |
              +-----------------+-----------------+
              |                                   |
     +--------v---------+                +--------v---------+
     |   Auth Service   |                |   Cloud Service  |
     |     FastAPI      |                |     FastAPI      |
     | Users, JWT,      |                | Files, Buckets,  |
     | Sessions         |                | S3 Operations   |
     +--------+---------+                +--------+---------+
              |                                   |       |
              |                                   |       |
       +------v------+                 +----------v--+  +--v-----------+
       | PostgreSQL  |                 | PostgreSQL  |  |    RustFS    |
       | Auth Data   |                 | Cloud Data  |  | S3 Objects   |
       +-------------+                 +-------------+  +--------------+
```

The services have separate responsibilities and data ownership. PostgreSQL may run as one infrastructure instance with separate databases or schemas for each service. RustFS stores object content and S3-managed attributes.

## 3. Microservices

### 3.1 Authentication Service

**Responsibility:** User identity, authentication, and session management.

**Functional requirements:**

- User registration.
- Sign-in using email and password.
- Access JWT issuance and refresh-token management.
- Token refresh and revocation.
- User profile retrieval and updates.
- Password changes.
- Active session management.
- Authentication and authorization information for the Cloud Service.

### 3.2 Cloud Service

**Responsibility:** File management and integration with RustFS through its S3-compatible API.

**Functional requirements:**

- User bucket creation and management.
- File upload and download.
- Virtual folder organization using S3 object key prefixes.
- Object copying and moving.
- File deletion and object version restoration.
- Object listing, filtering, and sorting.
- Object metadata and tag management.
- Presigned URL generation.
- Multipart uploads for large files.
- Storage usage reporting and per-user quota enforcement.

## 4. S3 API Feature Coverage

| Category | Target capabilities |
|---|---|
| Buckets | Create, List, Delete, Head |
| Objects | Put, Get, Head, Delete, Copy |
| Object listing | ListObjectsV2, prefix filtering, pagination |
| Multipart upload | CreateMultipartUpload, UploadPart, CompleteMultipartUpload, AbortMultipartUpload, ListParts |
| Presigned URLs | Time-limited download and upload URLs |
| Versioning | Object version history and restoration |
| Metadata | Content-Type and custom metadata |
| Tagging | Set, read, and remove object tags |
| Object Lock | Retention and Legal Hold |
| Lifecycle | Object expiration and retention rules |
| Bucket policies | Bucket-level access policies |
| Encryption | Server-side object encryption, where supported |
| Batch deletion | Delete multiple objects in one request |

**Compatibility requirement:** Advanced capabilities must be validated against the selected RustFS version. Features unsupported by RustFS must be documented and must not be advertised as functional endpoints.

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI |
| Object storage | RustFS |
| S3 client | aioboto3 / aiobotocore |
| Relational database | PostgreSQL |
| ORM | SQLAlchemy 2.0 Async |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Authentication | JWT, Argon2 password hashing |
| Tests | pytest, HTTPX |
| Container orchestration | Docker Compose |
| API documentation | OpenAPI / Swagger UI |

## 6. Data Storage Model

- **Auth PostgreSQL data:** Users, credentials, refresh tokens, and sessions.
- **Cloud PostgreSQL data:** Bucket ownership, file records and application metadata, storage quotas, and access permissions.
- **RustFS:** File contents, object versions, object tags, and other S3-managed attributes supported by the deployment.
- **JWT:** Identifies an authenticated user making requests to the Cloud Service.
- **Data isolation:** Users can access only their own storage resources unless access has been explicitly granted.

## 7. Non-Functional Requirements

- Asynchronous HTTP request handling.
- Streaming file transfers without buffering entire files in application memory.
- Large-file support using multipart uploads.
- Per-user storage quota limits.
- Resource ownership verification on protected operations.
- Protection against unauthorized access.
- Centralized structured logging.
- Health-check endpoints for both microservices.
- Consistent S3 error translation into HTTP API responses.
- Cleanup and expiration handling for abandoned multipart uploads.
- Unit and integration test coverage.
- One-command local environment startup using Docker Compose.

## 8. Proposed Repository Structure

```text
cloud-storage/
├── auth-service/
│   ├── api/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── tests/
│
├── cloud-service/
│   ├── api/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── tests/
│
├── migrations/
├── infrastructure/
├── scripts/
├── docker-compose.yml
├── .env.example
└── README.md
```

## 9. Architectural Principles and Scope

- Maintain two independently deployable FastAPI microservices.
- Keep authentication logic within the Auth Service and storage operations within the Cloud Service.
- Use PostgreSQL for structured application data and RustFS for object storage.
- Access RustFS through an S3-compatible client rather than a custom storage protocol.
- Provide an **application-specific REST API built on top of S3**, not a complete replacement implementation of the Amazon S3 protocol.
- Expose S3 capabilities while enforcing application-level authentication, authorization, user isolation, and quotas.
