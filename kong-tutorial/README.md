# Kong API Gateway Kubernetes Tutorial
This repository contains all the code needed to follow along with **[YouTube Tutorial](https://youtu.be/rTcj7znJVZc)**.

## Part 1: Basic Setup (Without Kong)

### 1. Apply the starter manifests:
```bash
kubectl apply -f ./app
```

### 2. Test the API (Basic Setup):
```bash
# Add grades
curl -X POST http://localhost:<port>/grades \
  -H "Content-Type: application/json" \
  -d '{"name": "Harry", "subject": "Defense Against Dark Arts", "score": 95}'

curl -X POST http://localhost:<port>/grades \
  -H "Content-Type: application/json" \
  -d '{"name": "Ron", "subject": "Charms", "score": 82}'

curl -X POST http://localhost:<port>/grades \
  -H "Content-Type: application/json" \
  -d '{"name": "Hermione", "subject": "Potions", "score": 98}'

# Get all grades
curl http://localhost:<port>/grades
```

## Part 2: Kong API Gateway Implementation

### 1. Kong Plugin Templates
```bash
kubectl apply -f ./kong
```

### 2. Test API with Kong Security:
```bash
# Add grades
curl -X POST http://localhost:<port>/grades \
  -H "apikey: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Harry", "subject": "Defense Against Dark Arts", "score": 95}'

# Get all grades
curl http://localhost:<port>/grades -H "apikey: your-secret-key"
```