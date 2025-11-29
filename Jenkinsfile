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
                    // Prevent later stages from running
                    throw new org.jenkinsci.plugins.workflow.steps.FlowInterruptedException("Exiting on main branch")
                }
            }
        }

        stage('Checkout') {
            steps {
                checkout scm
                sh "echo 'Current branch: ${env.BRANCH_NAME}'"
            }
        }

        stage('Rewrite Image Paths') {
            steps {
                // Single shell script - run Python script (ruamel.yaml) that updates files safely
                sh '''
                    bash -lc <<'BASH'
                    set -euo pipefail

                    # Ensure python deps available; install locally to avoid system changes
                    python3 -m pip install --user ruamel.yaml >/dev/null 2>&1 || true
                    export PATH="$HOME/.local/bin:$PATH"

                    export LOCAL_REPO="myrepo.local"
                    # Run script (it will update files in-place). Use --dry-run to preview
                    python3 scripts/update_images.py || true
                    BASH
                    '''
            }
        }

        stage('Create Branch, Commit & Open PR') {
            when {
                not { branch 'main' }
            }
            steps {
                withCredentials([usernamePassword(credentialsId: 'aa53f87f-dcf2-40cb-b44b-ed68bb9f0271', usernameVariable: 'GIT_USERNAME', passwordVariable: 'GIT_PASSWORD')]) {
                    sh '''
                        bash -lc <<'BASH'
                        set -euo pipefail

                        # Configure git
                        git config user.name "jenkins"
                        git config user.email "jenkins@ci.local"

                        # Only continue if there are changes
                        git add .
                        if git diff --cached --quiet; then
                          echo "No changes detected, skipping branch/PR creation."
                          exit 0
                        fi

                        # Create a topic branch
                        BRANCH_NAME_LOCAL="update-images-$(date +%Y%m%d%H%M%S)"
                        git commit -m "Rewrite image paths to $LOCAL_REPO"

                        ORIGIN_URL=$(git config --get remote.origin.url || true)
                        if [ -z "$ORIGIN_URL" ]; then
                          echo "No remote origin configured; aborting push."
                          exit 1
                        fi

                        # Convert SSH origin to https if needed
                        if echo "$ORIGIN_URL" | grep -q "git@"; then
                          ORIGIN_URL=$(echo "$ORIGIN_URL" | sed -E "s#git@([^:]+):#https://\1/#")
                        fi
                        AUTH_TARGET=$(echo "$ORIGIN_URL" | sed -E "s#https?://##")

                        # Create and push branch
                        git branch -M "$BRANCH_NAME_LOCAL"

                        git push "https://${GIT_USERNAME}:${GIT_PASSWORD}@${AUTH_TARGET}" HEAD:refs/heads/${BRANCH_NAME_LOCAL}

                        # Attempt to create a PR using GitHub CLI if available
                        if command -v gh >/dev/null 2>&1; then
                          echo "Creating PR with gh"
                          gh pr create --fill --base ${BRANCH_NAME} --head ${BRANCH_NAME_LOCAL} || true
                        else
                          echo "gh CLI not available; pushed branch ${BRANCH_NAME_LOCAL}."
                          echo "Open a pull request from ${BRANCH_NAME_LOCAL} into ${BRANCH_NAME} in your Git host."
                        fi
                        BASH
                        '''
                }
            }
        }
    }
}