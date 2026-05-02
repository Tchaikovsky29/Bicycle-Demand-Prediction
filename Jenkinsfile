pipeline {
    agent any

    environment {
        DOCKERHUB_USERNAME = "tchaikovsky29"
        ROOT_IMAGE         = "${DOCKERHUB_USERNAME}/env-base-image"
        PIPELINE_IMAGE     = "${DOCKERHUB_USERNAME}/my-app-pipeline"

        PIPELINE_DOCKERFILE = "src/pipeline/Dockerfile"
        PIPELINE_TRIGGER    = "src/pipeline/inference_transformer.py"
        ROOT_SRC_DIR        = "src/"
        ROOT_DOCKERFILE     = "Dockerfile"
    }

    stages {

        stage('Detect Changes') {
            steps {
                script {
                    def changedFiles = sh(
                        script: "git diff --name-only HEAD~1 HEAD",
                        returnStdout: true
                    ).trim().split('\n') as List

                    echo "Changed files:\n${changedFiles.join('\n')}"

                    def pipelineExcludes = [env.PIPELINE_TRIGGER, env.PIPELINE_DOCKERFILE]

                    env.BUILD_PIPELINE = changedFiles.any { f ->
                        f == env.PIPELINE_TRIGGER || f == env.PIPELINE_DOCKERFILE
                    } ? 'true' : 'false'

                    env.BUILD_ROOT = changedFiles.any { f ->
                        f == env.ROOT_DOCKERFILE ||
                        (f.startsWith(env.ROOT_SRC_DIR) && !(f in pipelineExcludes))
                    } ? 'true' : 'false'

                    echo "Build pipeline image : ${env.BUILD_PIPELINE}"
                    echo "Build root image     : ${env.BUILD_ROOT}"
                }
            }
        }

        stage('Build & Push Pipeline Image') {
            when { expression { env.BUILD_PIPELINE == 'true' } }
            agent { label 'kaniko' }
            steps {
                container('kaniko') {
                    sh """
                        /kaniko/executor \
                            --context=${WORKSPACE} \
                            --dockerfile=${WORKSPACE}/${PIPELINE_DOCKERFILE} \
                            --destination=${PIPELINE_IMAGE}:${GIT_COMMIT.take(7)} \
                            --destination=${PIPELINE_IMAGE}:latest
                    """
                }
            }
        }

        stage('Build & Push Root Image') {
            when { expression { env.BUILD_ROOT == 'true' } }
            agent { label 'kaniko' }
            steps {
                container('kaniko') {
                    sh """
                        /kaniko/executor \
                            --context=${WORKSPACE} \
                            --dockerfile=${WORKSPACE}/${ROOT_DOCKERFILE} \
                            --destination=${ROOT_IMAGE}:${GIT_COMMIT.take(7)} \
                            --destination=${ROOT_IMAGE}:latest
                    """
                }
            }
        }

        stage('No Builds Triggered') {
            when {
                expression {
                    env.BUILD_PIPELINE == 'false' && env.BUILD_ROOT == 'false'
                }
            }
            steps {
                echo 'No relevant files changed. Skipping all Docker builds.'
            }
        }
    }

    post {
        success { echo "Pipeline finished successfully." }
        failure { echo "Pipeline failed — check the logs above." }
    }
}