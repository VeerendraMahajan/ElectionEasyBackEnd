# Testing & Verification Guide

## 1. Live API Endpoint Verification
You can verify the running VoterLens system using HTTP requests or curl:

### Health & Readiness Checks
```bash
# Check service liveness
curl http://localhost:8001/health

# Check database & service readiness
curl http://localhost:8001/ready
```

### Document Upload
```bash
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
  -H "accept: application/json" \
  -F "file=@sample_data/PAN_076_7_1.pdf"
```

### Query Records in Ascending Serial Order
```bash
# Default query returns records sorted by serial number ascending (1, 2, 3...)
curl "http://localhost:8001/api/v1/records?limit=10"

# Specific document records
curl "http://localhost:8001/api/v1/documents/{document_id}/records"
```

---

## 2. Interactive API Testing (Swagger & Postman)
- **Swagger UI**: Visit [http://localhost:8001/docs](http://localhost:8001/docs) in your browser.
- **ReDoc**: Visit [http://localhost:8001/redoc](http://localhost:8001/redoc).
- **Postman**: Pre-configured collection files are available in:
  - Collection: [`postman/VoterLens.postman_collection.json`](../postman/VoterLens.postman_collection.json)
  - Environment: [`postman/VoterLens.postman_environment.json`](../postman/VoterLens.postman_environment.json)

---

## 3. Database Verification
To inspect records directly in PostgreSQL:
```bash
# Verify record count
docker exec voterlens_postgres psql -U postgres -d voterlens_db -c "SELECT count(*) FROM person_records;"

# Verify serial number ascending sequence
docker exec voterlens_postgres psql -U postgres -d voterlens_db -c "SELECT serial_number, name_hi, id_number, house_number, age FROM person_records ORDER BY serial_number ASC NULLS LAST LIMIT 10;"
```
