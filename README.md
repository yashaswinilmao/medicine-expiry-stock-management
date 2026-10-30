# MediTrack — Medicine Expiry & Stock Management

A Flask + SQLite web application prepared for a DevOps CI/CD case study. It includes a dashboard, medicine CRUD, expiry alerts, stock reports, Docker packaging, Jenkins pipeline, and Kubernetes manifests.

## Features
- Dashboard with medicine count, expired count, expiring-soon count and total units
- Add, edit, delete and search medicine records
- Expiry alerts (expired and expiring within 30 days)
- Low-stock status (10 units or fewer)
- Stock quantity by category and estimated stock value
- SQLite database persisted at `/data/medicines.db` in the container
- `/health` endpoint for container/Kubernetes health checks

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Run tests

```bash
pytest -q
```

## Run with Docker

```bash
docker build -t medicine-expiry-stock:local .
docker run --rm -p 5000:5000 -v medicine-data:/data medicine-expiry-stock:local
```

Open http://localhost:5000

## Push image to Docker Hub

Replace `YOUR_DOCKERHUB_USERNAME` with your Docker Hub username.

```bash
docker login
docker build -t YOUR_DOCKERHUB_USERNAME/medicine-expiry-stock:latest .
docker push YOUR_DOCKERHUB_USERNAME/medicine-expiry-stock:latest
```

## Kubernetes deployment

1. Update the image name in `k8s/deployment.yaml`.
2. Ensure your cluster is running and `kubectl` is configured.
3. Apply manifests:

```bash
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl get pods
kubectl get svc
```

For Minikube, access the service using:

```bash
minikube service medicine-stock-service
```

For a NodePort cluster, browse to `http://<node-ip>:30080`.

**SQLite note:** The supplied PVC is a simple teaching/demo setup. SQLite with two replicas and a single ReadWriteOnce volume is not a production-grade multi-replica database design. For a production deployment, use PostgreSQL or another managed database, and configure appropriate persistent storage and secrets.

## Jenkins CI/CD setup

The included `Jenkinsfile` performs:
1. Checkout from Git
2. Install dependencies and run pytest
3. Build a Docker image tagged with the Jenkins build number and `latest`
4. Push both tags to Docker Hub
5. Apply Kubernetes manifests and wait for rollout

Before running the pipeline:
- Install/configure Git, Python 3, Docker CLI/daemon, `kubectl`, and Kubernetes credentials on the Jenkins agent.
- Add a Jenkins username/password credential with ID `dockerhub-creds` for Docker Hub.
- Replace `YOUR_DOCKERHUB_USERNAME` in the `DOCKER_IMAGE` value in `Jenkinsfile`.
- Configure the Jenkins job as a Pipeline from SCM and point it to this Git repository.
- Configure a webhook from GitHub to Jenkins for immediate push-triggered builds. The sample Jenkinsfile also uses `pollSCM` as a fallback; this polls every two minutes.
- Ensure the Jenkins agent's kubeconfig/context can access the target cluster.

**Important:** The pipeline's deploy stage assumes a Kubernetes cluster is already available to Jenkins. Do not commit kubeconfig files, Docker passwords, or real production secrets to Git.

## Suggested GitHub repository structure

```text
medicine-expiry-stock-management/
├── app.py
├── requirements.txt
├── Dockerfile
├── Jenkinsfile
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── pvc.yaml
├── templates/
├── static/
└── tests/
```

## Case study demonstration

1. Add a medicine record through the UI.
2. Show it in the stock table and dashboard.
3. Add an old expiry date or low quantity to demonstrate alerts.
4. Push a small code change to GitHub.
5. Show Jenkins checkout, test, Docker build, Docker Hub push and Kubernetes rollout.
6. Refresh the deployed site to verify the new version.

## Limitations / production considerations
- This is an academic demo, not a validated pharmacy/medical inventory product.
- It does not provide prescriptions, patient records, regulatory compliance, or automatic notifications.
- Expiry status is based on the server's current date.
- Change the default Flask secret key before deployment.
- For production, use authentication/authorization, audit logs, backups, secure secrets, database migrations, and a production database.
