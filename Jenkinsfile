pipeline {
    agent any
    environment {
        // Create a Jenkins credential with ID 'dockerhub-creds' (username/password).
        DOCKER_IMAGE = "YOUR_DOCKERHUB_USERNAME/medicine-expiry-stock"
        K8S_NAMESPACE = "default"
    }
    triggers { pollSCM('H/2 * * * *') }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Install and Test') {
            steps {
                sh 'python3 -m venv .venv'
                sh '. .venv/bin/activate && pip install -r requirements.txt'
                sh '. .venv/bin/activate && pytest -q --junitxml=pytest.xml'
            }
        }
        stage('Build Docker Image') {
            steps {
                sh 'docker build -t $DOCKER_IMAGE:$BUILD_NUMBER -t $DOCKER_IMAGE:latest .'
            }
        }
        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh 'echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin'
                    sh 'docker push $DOCKER_IMAGE:$BUILD_NUMBER'
                    sh 'docker push $DOCKER_IMAGE:latest'
                    sh 'docker logout'
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                // Jenkins agent must have kubectl and access to the target cluster.
                sh 'sed "s|YOUR_DOCKERHUB_USERNAME/medicine-expiry-stock|$DOCKER_IMAGE|g" k8s/deployment.yaml > /tmp/medicine-deployment.yaml'
                sh 'sed -i "s|:latest|:$BUILD_NUMBER|g" /tmp/medicine-deployment.yaml'
                sh 'kubectl apply -f k8s/pvc.yaml'
                sh 'kubectl apply -f /tmp/medicine-deployment.yaml'
                sh 'kubectl apply -f k8s/service.yaml'
                sh 'kubectl rollout status deployment/medicine-stock --timeout=180s'
            }
        }
    }
    post {
        always { archiveArtifacts artifacts: 'pytest.xml', allowEmptyArchive: true }
        success { echo 'Medicine Stock application deployed successfully.' }
        failure { echo 'Pipeline failed. Check the stage logs.' }
    }
}
