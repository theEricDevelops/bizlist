# BizList API Project Overview

This document outlines the overall architecture and design decisions for the BizList API backend.

## I. Project Goals

* **Primary Goal:** To create a robust and scalable API for searching business contacts from various online sources.
* **Secondary Goals:**  ease of maintenance, future extensibility, and security.

## II. Technology Stack

This section details the chosen technologies and the rationale behind those choices.

### A. Backend Framework: FastAPI (Python)

**Rationale:**

* **Performance:** FastAPI is known for its high performance due to its use of ASGI and Starlette.  This is crucial for handling potentially large numbers of search requests.
* **Ease of Use:** FastAPI's intuitive syntax and automatic API documentation generation (using OpenAPI/Swagger) significantly reduce development time and improve maintainability.
* **Data Handling:** Python's rich ecosystem of data processing libraries (e.g., Pandas, NumPy) makes it well-suited for handling and cleaning the extracted contact data.
* **Community Support:** FastAPI has a growing and active community, providing ample resources and support.

**Alternatives Considered:**  

* Node.js with Express: While a viable option, FastAPI offered a better balance of performance, ease of use, and data handling capabilities for this project.

### B. Database: PostgreSQL

**Rationale:**

* **Relational Data:** PostgreSQL's relational model is well-suited for structured data like contact information.
* **Scalability:** PostgreSQL offers excellent scalability to handle growing data volumes.
* **Features:**  PostgreSQL provides features like indexing and efficient querying, crucial for optimizing search performance.

**Alternatives Considered:**

* MongoDB: Considered for its flexibility, but PostgreSQL's relational model was deemed more appropriate for the structured nature of the contact data.

### C. Other Technologies

* **Web Scraping Library:** Beautiful Soup (Python) - Chosen for its ease of use and robust parsing capabilities.
* **Testing Framework:** pytest (Python) - Chosen for its simplicity and extensive features.
* **Deployment Platform:**  For development, we are going to focus on docker containers for postgresql and any other providers (celery, rabbitmq, etc) we might need.

## III. API Design

This section describes the key design aspects of the API.

### A. Endpoints

The API will primarily use POST requests for search operations to allow for flexible filtering and sorting.

* `/search`:  This endpoint accepts a JSON payload with search criteria and returns a paginated list of contacts.

    **Request Payload (Example):**

    ```json
    {
      "keywords": "Software Engineer",
      "industry": "Technology",
      "location": "San Francisco",
      "page": 1,
      "limit": 20
    }
    ```

    **Response (Example):**

    ```json
    {
      "contacts": [
        { "name": "John Doe", "email": "john.doe@example.com", ... },
        { "name": "Jane Smith", "email": "jane.smith@example.com", ... },
        // ... more contacts
      ],
      "total": 150, // Total number of contacts matching the criteria
      "page": 1,
      "limit": 20
    }
    ```

* `/health`: A simple health check endpoint to verify API availability.  Returns a 200 OK status code if the API is running correctly.

### B. Data Model (PostgreSQL Schema Example)

```sql
CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    title VARCHAR(255),
    company VARCHAR(255),
    industry VARCHAR(255),
    location VARCHAR(255)
    -- Add other relevant fields as needed
);
```

### C. Error Handling

The API will use standard HTTP status codes to indicate success or failure. Error responses will be in JSON format, including a descriptive error message and an error code.

Example Error Response:

```json
{
  "error": "Invalid search parameters",
  "code": 400,
  "message": "The 'keywords' parameter is required."
}
```

## IV. Development Process

* **Version Control:** Git (GitHub)
* **Issue Tracking:** GitHub Issues
* **Development Workflow:** Vibe coding ;).

## V. Future Considerations

* **Scalability:** Strategies for scaling the API to handle increased traffic and data volume.
* **Data Enrichment:** Plans for integrating with data enrichment services.
* **Advanced Search Features:**  Ideas for implementing more advanced search capabilities.
