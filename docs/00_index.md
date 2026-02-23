# Event Service GUI - Architecture Documentation

> **Generated**: 2024  
> **Target Audience**: Technical leads and architects  
> **Documentation Level**: High detail (design patterns, interfaces, deployment)  
> **Standard**: C4 Model (Context, Container, Component, Code)

## Quick Navigation

### 📋 Core Architecture
- [01 - Architecture Overview](01_architecture_overview.md) - System design principles and layers
- [02 - C4 Context Diagram](02_c4_context.md) - System scope and external dependencies
- [03 - C4 Container Diagram](03_c4_container.md) - Major deployable components
- [04 - C4 Component Diagram](04_c4_components.md) - Internal component structure

### 🗄️ Data & Integration
- [05 - Data Models](05_data_models.md) - Core domain entities and data structures
- [07 - Integration Points](07_integration_points.md) - Microservice interactions

### 🏗️ Design & Operations
- [06 - Design Patterns](06_design_patterns.md) - Architectural patterns and best practices
- [08 - Deployment Architecture](08_deployment.md) - Infrastructure and deployment strategy

## 🎯 Project Summary

**Event Service GUI** is a web-based administration interface for managing sporting events. It enables:

✅ Event and competition management  
✅ Contestant registration and seeding  
✅ Race planning and live control  
✅ Real-time result tracking  
✅ Administrative reporting  

### 🏛️ Architecture Pattern

```
User → Browser → Web Server (Gunicorn/aiohttp)
                    ↓
            Views (Request Handlers)
                    ↓
            Services (Business Logic)
                    ↓
            Adapters (Service Integration)
                    ↓
            Microservices (Event, User, Race, etc.)
                    ↓
            MongoDB (Shared Data Store)
```

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| **Framework** | aiohttp (async Python web framework) |
| **Language** | Python 3.13+ |
| **Frontend** | Jinja2 templates, HTML5, CSS3, JavaScript |
| **Authentication** | JWT tokens + encrypted session cookies |
| **Database** | MongoDB |
| **Server** | Gunicorn + aiohttp |
| **Containerization** | Docker |
| **Configuration** | Environment variables + JSON files |

## 📊 Key Statistics

- **Views**: 12 main views (Events, Raceplans, Contestants, Control, etc.)
- **Services**: 11 adapter classes integrating with microservices
- **Configuration Files**: 5 JSON config files (formats, clubs, settings)
- **Template Files**: 15+ Jinja2 templates
- **External Services**: 5 microservices (Event, User, Competition Format, Race, Photo)
- **Code Layers**: 4 (Templates, Views, Services, Adapters)

## 🚀 Deployment

### Development
Docker Compose with local services

### Staging/Production
Kubernetes with:
- Load balancing (NGINX Ingress)
- Multiple replicas for HA
- Health checks and auto-recovery
- MongoDB replica set
- SSL/TLS encryption

## 🔑 Key Design Principles

1. **Separation of Concerns**: Clear layer boundaries (View → Service → Adapter)
2. **Async-First**: Non-blocking I/O for high concurrency
3. **Adapter Pattern**: Decoupled microservice integration
4. **Configuration-Driven**: Environment-based multi-environment support
5. **Stateless Design**: Enables horizontal scaling

## 📚 Documentation Structure

Each document in this architecture follows the **C4 Model**:

- **Context**: What the system does and who uses it
- **Containers**: Technologies and deployment containers
- **Components**: Internal modules and their responsibilities
- **Code**: Implementation details (class, function level)

## 🎓 Reading Guide

**New to the project?** Start here:
1. [Architecture Overview](01_architecture_overview.md) - Understand the design
2. [C4 Context](02_c4_context.md) - See the big picture
3. [C4 Container](03_c4_container.md) - Deployable components

**Need deployment details?**
→ Go to [Deployment Architecture](08_deployment.md)

**Implementing a new feature?**
→ Read [Design Patterns](06_design_patterns.md) and [Data Models](05_data_models.md)

**Integrating a new service?**
→ Read [Integration Points](07_integration_points.md)

## 📞 Maintainers

- Architecture: Technical Leads
- Documentation: Development Team
- Last Updated: 2024

---

**Next Step**: Start with [Architecture Overview](01_architecture_overview.md) for a complete understanding of the system design.
