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

                    YQ_NO_LOCK=true yq -i '
                      .. | select(tag == "!!map") |
                      with(.image.repository?; . = "'$LOCAL_REPO'/" + (. | split("/")[-1]))
                    ' "$f"

                    YQ_NO_LOCK=true yq -i '
                      .. | select(tag == "!!str" and (. | test("^.*/.*:.*$"))) |
                      sub("^[^/]+/([^:]+):", "'$LOCAL_REPO'/\\1:")
                    ' "$f"

                    # Rewrite hub: fields if non-empty
                    YQ_NO_LOCK=true yq -i '
                      .. |
                      select(tag == "!!map") |
                      with(.hub; if . != "" and . != null then "'"$LOCAL_REPO"'" else . end)
                    ' "$f"
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