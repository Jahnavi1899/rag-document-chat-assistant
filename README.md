# RAG Document Chat Application

A full-stack Retrieval-Augmented Generation (RAG) application that allows users to upload documents and have AI-powered conversations about their content.

## Overview

This application enables users to:
- Upload PDF and TXT documents
- Automatically process and index documents using vector embeddings
- Chat with documents using natural language
- Maintain conversation history per document

## Architecture

### AWS Production Architecture

```
                                    ┌─────────────────────────────────────────────────────────────┐
                                    │                         AWS Cloud                           │
                                    │  ┌───────────────────────────────────────────────────────┐  │
                                    │  │                          VPC                          │  │
                                    │  │                                                       │  │
        ┌──────────┐                │  │   ┌─────────────────────────────────────────────┐     │  │
        │          │                │  │   │              Public Subnets                 │     │  │
        │  Users   │───────────────▶│  │   │  ┌───────────────────────────────────────┐  │     │  │
        │          │                │  │   │  │    Application Load Balancer (ALB)    │  │     │  │
        └──────────┘                │  │   │  │         ┌───────────┬───────────┐     │  │     │  │
                                    │  │   │  │         │ /         │ /api/*    │     │  │     │  │
                                    │  │   │  └─────────┴─────┬─────┴─────┬─────┴─────┘  │     │  │
                                    │  │   │    NAT Gateway   │           │              │     │  │
                                    │  │   └──────────────────┼───────────┼──────────────┘     │  │
                                    │  │                      │           │                    │  │
                                    │  │   ┌──────────────────┼───────────┼──────────────┐     │  │
                                    │  │   │                  │  Private Subnets         │     │  │
                                    │  │   │                  ▼           ▼              │     │  │
                                    │  │   │   ┌──────────────────────────────────────┐  │     │  │
                                    │  │   │   │           ECS Fargate Cluster        │  │     │  │
                                    │  │   │   │  ┌──────────┐ ┌──────────┐ ┌───────┐ │  │     │  │
                                    │  │   │   │  │ Frontend │ │ Backend  │ │Worker │ │  │     │  │
                                    │  │   │   │  │ Service  │ │ Service  │ │Service│ │  │     │  │
                                    │  │   │   │  └──────────┘ └────┬─────┘ └───┬───┘ │  │     │  │
                                    │  │   │   └────────────────────┼───────────┼─────┘  │     │  │
                                    │  │   │                        │           │        │     │  │
                                    │  │   │         ┌──────────────┼───────────┤        │     │  │
                                    │  │   │         │              │           │        │     │  │
                                    │  │   │         ▼              ▼           ▼        │     │  │
                                    │  │   │   ┌──────────┐  ┌───────────┐  ┌───────┐    │     │  │
                                    │  │   │   │   RDS    │  │ElastiCache│  │  EFS  │    │     │  │
                                    │  │   │   │PostgreSQL│  │  (Redis)  │  │ChromaDB    │     │  │
                                    │  │   │   └──────────┘  └───────────┘  └───────┘    │     │  │
                                    │  │   └─────────────────────────────────────────────┘     │  │
                                    │  └───────────────────────────────────────────────────────┘  │
                                    │                              │                              │
                                    │                              ▼                              │
                                    │                        ┌──────────┐                         │
                                    │                        │    S3    │                         │
                                    │                        │(Documents)                         │
                                    │                        └──────────┘                         │
                                    └─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework for building APIs
- **Celery** - Distributed task queue for async document processing
- **PostgreSQL** - Relational database for metadata and chat history
- **Redis** - Message broker for Celery and caching layer
- **ChromaDB** - Vector database for document embeddings
- **LangChain** - Framework for building LLM applications
- **SentenceTransformers** - Local embedding model (all-MiniLM-L6-v2)
- **OpenAI GPT** - LLM for generating responses

### Frontend
- **React** - UI library
- **TypeScript** 
- **Vite** - Build tool and dev server

### Infrastructure
- **Docker & Docker Compose** - Local development containerization
- **Nginx** - Reverse proxy for frontend and API routing
- **Terraform** - Infrastructure as Code for AWS deployment
- **AWS Services** - ECS Fargate, RDS, ElastiCache, S3, EFS, ALB

## Project Structure

```
.
├── app/                          # Backend application
│   ├── core/
│   │   ├── config.py             # Configuration management
│   │   ├── database.py           # Database connection
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── middleware.py         # Session management middleware
│   │   ├── session.py            # Session utilities
│   │   ├── celery_worker.py      # Celery app configuration
│   │   └── tasks.py              # Async tasks (RAG ingestion)
│   ├── schemas/
│   │   └── document.py           # Pydantic schemas
│   └── main.py                   # FastAPI application entry point
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── App.tsx               # Main application component
│   │   ├── ChatComponent.tsx     # Chat interface
│   │   ├── UploadComponent.tsx   # Document upload component
│   │   └── types.ts              # TypeScript type definitions
│   └── ...
├── terraform/                    # Infrastructure as Code
│   ├── modules/
│   │   ├── networking/           # VPC, subnets, gateways
│   │   ├── storage/              # S3, EFS
│   │   ├── database/             # RDS PostgreSQL
│   │   ├── cache/                # ElastiCache Redis
│   │   ├── alb/                  # Application Load Balancer
│   │   └── ecs/                  # ECS Fargate services
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── docker-compose.yml            # Local development orchestration
├── Dockerfile                    # Backend container image
├── Dockerfile.frontend           # Frontend container image
├── nginx.conf                    # Nginx reverse proxy configuration
└── requirements.txt              # Python dependencies
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- OpenAI API key

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rag-document-chat
   ```

2. **Create environment file**
   
   Create a `.env` file in the project root:
   ```env
   # Database
   DB_USER=postgres
   DB_PASSWORD=your_secure_password
   DB_NAME=ragapp
   
   # OpenAI
   OPENAI_API_KEY=sk-your-openai-api-key
   
   # AWS (for S3 storage/ local storage for development)
   AWS_REGION=us-east-1
   S3_BUCKET=your-bucket-name
   CHROMA_PATH=/app/chroma_db
   ```

3. **Start the application**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Frontend: http://localhost:5173
   - API Documentation: http://localhost:8000/docs

## How It Works

### Document Upload Flow

1. User uploads a PDF or TXT file through the frontend
2. FastAPI receives the file and stores it in S3 / local storage (for local development)
3. Document metadata is saved to PostgreSQL
4. A Celery task is dispatched for async processing
5. Frontend polls the job status endpoint

### RAG Ingestion (Celery Worker)

1. Worker downloads the document from S3 / local storage (for local development)
2. Document is loaded and split into chunks using LangChain
3. Chunks are embedded using SentenceTransformers (all-MiniLM-L6-v2)
4. Embeddings are stored in ChromaDB with a document-specific collection
5. Document status is updated to "processed"

### Chat Flow

1. User sends a question about a specific document
2. Question is optionally rephrased using chat history (query condensation)
3. Relevant chunks are retrieved from ChromaDB
4. Context + question are sent to OpenAI GPT
5. Response is streamed back to the frontend
6. Conversation is saved to PostgreSQL for history

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | API health check |
| GET | `/health/db` | Database connectivity check |
| POST | `/api/v1/documents/upload` | Upload a document |
| GET | `/api/v1/documents` | List processed documents |
| GET | `/api/v1/jobs/status/{task_id}` | Check ingestion job status |
| POST | `/api/v1/documents/{id}/chat` | Chat with a document |

## Session Management

The application uses cookie-based anonymous sessions:

- Sessions are automatically created for new users
- Each session has its own documents and chat histories
- Sessions expire after 7 days of inactivity
- Document access is scoped to the owning session

## Configuration

Key environment variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_HOST` | Redis hostname |
| `CELERY_BROKER_URL` | Celery broker URL (Redis) |
| `CELERY_RESULT_BACKEND` | Celery result backend (Redis) |
| `OPENAI_API_KEY` | OpenAI API key for GPT |
| `S3_BUCKET` | S3 bucket for document storage |
| `CHROMA_PATH` | Path for ChromaDB persistence |

## AWS Deployment

The `terraform/` directory contains Infrastructure as Code for deploying to AWS:

### Resources Created

- **Networking**: VPC, public/private subnets, NAT Gateway, Internet Gateway
- **Compute**: ECS Fargate cluster with frontend, backend, and worker services
- **Database**: RDS PostgreSQL (db.t3.micro)
- **Cache**: ElastiCache Redis (cache.t3.micro)
- **Storage**: S3 bucket for documents, EFS for ChromaDB
- **Load Balancing**: Application Load Balancer with path-based routing

### Deployment Steps

1. **Configure variables**
   ```bash
   cd terraform
   # Edit terraform.tfvars with your values
   ```

2. **Initialize and deploy**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

3. **Access the application**
   
   The ALB DNS name will be output after deployment.
