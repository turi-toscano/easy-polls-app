# Important Note

The application's code is out of the project's scope and is not developed by me: the microservices are taken for granted to create the Kubernetes cluster (both locally and in cloud). 

---

# Goal

This repository contains the source code of the Easy Polls application, the Kubernetes manifests required to deploy it, and the CI/CD workflow that automates its build and release inside the cluster running in AWS.

### Application

The application is a web app for creating instant polls: a user creates a question with a few answer options, gets a shareable link, and anyone with the link can vote. Results are available on a dedicated page that updates in real time showing the voting percentages. The application is split into three components, plus the MongoDB database:

- `frontend`: static web interface for creating polls.
- `poll-service`: exposes the API for creating polls and recording votes.
- `results-service`: exposes the API that returns the results of a given poll.

The database is **Amazon DocumentDB**, a managed MongoDB-compatible service that lives outside the cluster: this repository therefore contains no manifest related to data persistence.
The `HorizontalPodAutoscaler` is configured on the `results-service` only, which scales based on CPU utilization.

## Repository structure

```
├── frontend
│   ├── Dockerfile
│   └── html
│       ├── app.css
│       ├── index.html
│       ├── results.html
│       └── vote.html
├── k8s
│   ├── frontend-deployment.yml
│   ├── frontend-service.yml
│   ├── ingress.yml
│   ├── poll-service-deployment.yml
│   ├── poll-service-service.yml
│   ├── results-service-deployment.yml
│   ├── results-service-scaling.yml
│   └── results-service-service.yml
├── poll-service
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
└── results-service
    ├── Dockerfile
    ├── app.py
    └── requirements.txt
```

### k8s directory

The `k8s` directory contains the Kubernetes manifests that describe the desired state of the application inside the cluster. In particular:

- The `frontend` manifests define the frontend `Deployment`, with two replicas, and its `ClusterIP` `Service`. Routing of API calls is handled by the Ingress.
- The `poll-service` manifests define the service `Deployment`, with two replicas, and its `ClusterIP` `Service`.
- The `results-service` manifests define the service `Deployment`, its `ClusterIP` `Service` and the `HorizontalPodAutoscaler`, which scales the number of replicas from $2$ to $6$ based on average CPU utilization.
- `ingress.yml` defines the `Ingress` resource, which describes the routing rules based on the path prefix; these are handled by the nginx Ingress Controller, listening on NodePort $30080$ of the cluster nodes.

The manifests use three *placeholders*, which are replaced by the deployment workflow at release time, after the infrastructure has been created:

- `ECR_REGISTRY`: the address of the ECR registry.
- `IMAGE_TAG`: the image tag, corresponding to the commit hash.
- `DOCDB_ENDPOINT`: the endpoint of the DocumentDB cluster.

### Workflows

The `.github/workflows` directory contains the application's CI/CD workflow. There is a single workflow:

- `deploy.yml`: it runs on a push to the `main` branch, or manually, and it is also triggered automatically by the infrastructure provisioning workflow once the cluster has been configured. It builds the three container images and publishes them to Amazon ECR, tagging them with the commit hash; creates the `mongo-secret` Kubernetes secret from the repository's `MONGO_PASSWORD` secret; replaces the *placeholders* inside the manifests and applies them to the cluster; and finally waits for the rollout to complete.

---

# Setup

### Creating the environment and the secrets

For the deployment workflow to work correctly, an environment must be created and some secrets added. To create the environment, go to `Settings > Environments > New environment` and name it `production`; once created, the secrets can be added by clicking `Add environment secret` under `Environment secrets`:

- `AWS_ROLE_ARN`: the ARN of the IAM role created previously.
- `BASTION_SSH_PRIVATE_KEY`: use the Bastion Host private key generated for the infrastructure repository.
- `MONGO_PASSWORD`: the password that will be used for the DocumentDB instance.

### Deploying to the cluster

After every new push, or once the infrastructure provisioning workflow completes, the deployment workflow applies the Kubernetes manifests and waits for the new version to roll out.
