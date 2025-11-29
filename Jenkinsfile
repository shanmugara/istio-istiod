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
                // Single shell script - no nested sh blocks
                sh '''
                    set -euo pipefail

                    echo "Rewriting all image references to: $LOCAL_REPO ..."

                    # Find YAML files robustly
                    IFS=$'\n'
                    FILES=$(find . -type f \( -name "*.yaml" -o -name "*.yml" \) -print)

                    # Detect yq and whether it runs cleanly (catch memlock/permission failures)
                    YQ_CMD=$(command -v yq || true)
                    YQ_OK=0
                    YQ_MAJOR=0
                    if [ -n "$YQ_CMD" ]; then
                      echo "Found yq at $YQ_CMD — testing..."
                      YQ_OUT=$(yq --version 2>&1) || YQ_OUT="$(yq --version 2>&1 || true)"
                      echo "yq --version output: $YQ_OUT"
                      if echo "$YQ_OUT" | grep -qi "operation not permitted\|memlock"; then
                        echo "yq failed due to memlock/permission; will skip yq operations."
                        YQ_OK=0
                      else
                        # Try to extract major version number (works for common yq outputs)
                        MAJOR=$(echo "$YQ_OUT" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 | cut -d. -f1 || true)
                        if [ -n "$MAJOR" ]; then
                          YQ_MAJOR=$MAJOR
                        else
                          # Fallback: assume 3-style if "yq" prints something unexpected
                          YQ_MAJOR=3
                        fi
                        YQ_OK=1
                        echo "yq usable (major version: $YQ_MAJOR)"
                      fi
                    else
                      echo "yq not found — will skip structured YAML edits and use sed fallback."
                    fi

                    for f in $FILES; do
                      [ -f "$f" ] || continue
                      echo "Processing $f"

                      if [ "$YQ_OK" -eq 1 ]; then
                        # Try v3-style write first (safe if actual v3 present), ignore failures
                        if [ "$YQ_MAJOR" -lt 4 ]; then
                          yq w -i "$f" '**.image.repository' "$LOCAL_REPO" 2>/dev/null || true
                          yq w -i "$f" 'global.hub' "$LOCAL_REPO" 2>/dev/null || true
                        else
                          # Try a couple of v4-style commands; they may differ slightly across builds, so tolerate failures
                          # Set global.hub if present
                          yq eval -i '.global.hub = env(LOCAL_REPO)' "$f" 2>/dev/null || yq eval -i '.global.hub = strenv(LOCAL_REPO)' "$f" 2>/dev/null || true
                          # Try to update any image.repository occurrences; the exact path may vary so attempt a few patterns
                          yq eval -i '(.. | select(has("image")) | .image.repository) = env(LOCAL_REPO)' "$f" 2>/dev/null || yq eval -i '(.[] | select(has("image")) | .image.repository) = env(LOCAL_REPO)' "$f" 2>/dev/null || true
                        fi
                      else
                        echo "Skipping yq edits for $f"
                      fi

                      # Always perform a robust sed substitution for full image strings (image: registry/name:tag)
                      # Use a portable inline backup for sed then remove it
                      sed -E -i.bak "s#(image:[[:space:]]*)[^/[:space:]]*/#\1$LOCAL_REPO/#g" "$f" || true
                      rm -f "${f}.bak" || true

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
                withCredentials([usernamePassword(credentialsId: 'aa53f87f-dcf2-40cb-b44b-ed68bb9f0271', usernameVariable: 'GIT_USERNAME', passwordVariable: 'GIT_PASSWORD')]) {
                    sh '''
                        set -euo pipefail

                        git config user.name "jenkins"
                        git config user.email "jenkins@ci.local"

                        # Stage changes
                        git add .
                        if git diff --cached --quiet; then
                          echo "No changes. Skipping commit."
                          exit 0
                        fi

                        git commit -m "Rewrite image paths to $LOCAL_REPO"

                        ORIGIN_URL=$(git config --get remote.origin.url || true)
                        if [ -z "$ORIGIN_URL" ]; then
                          echo "No remote origin found, pushing to origin by name"
                          git push origin HEAD:${BRANCH_NAME}
                          exit 0
                        fi

                        # Convert SSH URL (git@host:org/repo.git) to https://host/org/repo.git
                        if echo "$ORIGIN_URL" | grep -q "git@"; then
                          ORIGIN_URL=$(echo "$ORIGIN_URL" | sed -E "s#git@([^:]+):#https://\1/#")
                        fi

                        # Remove protocol so we can inject credentials
                        AUTH_TARGET=$(echo "$ORIGIN_URL" | sed -E "s#https?://##")

                        # Push using injected credentials (safe for CI)
                        git push "https://${GIT_USERNAME}:${GIT_PASSWORD}@${AUTH_TARGET}" HEAD:${BRANCH_NAME}
                        '''
                }
            }
        }
    }
}