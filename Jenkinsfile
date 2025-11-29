pipeline {
    agent any

    environment {
        LOCAL_REPO = "docker.io/shanmugara"
    }

    options {
        skipDefaultCheckout()
    }

    stages {

        stage('Abort on main branch') {
            when {
                branch 'main'
            }
            steps {
                echo "This pipeline does not run on main branch. Exiting."
                script {
                    currentBuild.result = 'SUCCESS'
                }
            }
        }

        stage('Checkout') {
            steps {
                checkout scm
                sh "echo 'Current branch: ${env.GIT_BRANCH}'"
            }
        }

        stage('Rewrite Image Paths') {
            steps {
                sh '''
                  echo "Rewriting all image references to: $LOCAL_REPO ..."

                  FILES=$(find . -type f -name "*.yaml" -o -name "*.yml")

                  for f in $FILES; do
                    echo "Processing $f"

                    echo "Processing $f"
                            # Rewrite .image.repository
                            yq w -i "$f" '**.image.repository' "$LOCAL_REPO"

                            # Rewrite global.hub
                            yq w -i "$f" 'global.hub' "$LOCAL_REPO"

                            # Rewrite full image strings (image: registry/name:tag)
                            sed -i "s#image: [^/]*\/#image: $LOCAL_REPO/#g" "$f"
                  done
                '''
            }
        }

        stage('Review Results') {
            steps {
                sh '''
                  echo "Modified image references:"
                  grep -R "$LOCAL_REPO" -n . || true
                '''
            }
        }

        stage('Commit & Push to Branch') {
            when {
                not { branch 'main' }
            }
            steps {
            withCredentials([
                      usernamePassword(credentialsId: 'aa53f87f-dcf2-40cb-b44b-ed68bb9f0271', usernameVariable: 'GIT_USERNAME', passwordVariable: 'GIT_PASSWORD')
                    ]) {
                sh '''
                  git config user.name "jenkins"
                  git config user.email "jenkins@ci.local"

                  git add .
                  git diff --cached --quiet && echo "No changes. Skipping commit." && exit 0

                  git commit -m "Rewrite image paths to $LOCAL_REPO"
                  git push origin HEAD:${GIT_BRANCH}
                '''
                }
            }
        }
    }
}