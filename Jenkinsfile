pipeline {
    agent any
    
    environment {
        DOCKERHUB_USERNAME = "tchaikovsky29"
        ROOT_IMAGE         = "${DOCKERHUB_USERNAME}/env-base-image"
        PIPELINE_IMAGE     = "${DOCKERHUB_USERNAME}/inference-transformer"
        GIT_SSL_NO_VERIFY = 'true'
        PIPELINE_DOCKERFILE = "src/pipeline/Dockerfile"
        PIPELINE_TRIGGER    = "src/pipeline/inference_transformer.py"
        PIPELINE_DIRECTORY  = "src/pipeline/"
        ROOT_SRC_DIR        = "src/"
        ROOT_DOCKERFILE     = "Dockerfile"
    }

    stages {
        stage('Detect Changes') {
            steps {
                script {
                    def changedFiles = sh(
                        script: "git diff --name-only HEAD~1 HEAD 2>/dev/null || echo ''",
                        returnStdout: true
                    ).trim().split('\n') as List

                    def pipelineFiles = [
                        env.PIPELINE_TRIGGER,
                        env.PIPELINE_DOCKERFILE
                    ]

                    env.BUILD_PIPELINE = changedFiles.any { file ->
                        pipelineFiles.contains(file)
                    } ? 'true' : 'false'

                    env.BUILD_ROOT = changedFiles.any { file ->
                        (file.startsWith(env.ROOT_SRC_DIR) && !file.startsWith(env.PIPELINE_DIRECTORY)) ||
                        file.startsWith("config/")                                             ||
                        file == env.ROOT_DOCKERFILE
                    } ? 'true' : 'false'

                    echo "Changed files: ${changedFiles}"
                    echo "BUILD_PIPELINE=${env.BUILD_PIPELINE}"
                    echo "BUILD_ROOT=${env.BUILD_ROOT}"
                }
            }
        }

        stage('Build & Push Pipeline Image') {
            when { expression { env.BUILD_PIPELINE == 'true' } }
            agent { label 'kaniko' }
            steps {
                container('kaniko') {
                    script {
                        def shortCommit = env.GIT_COMMIT.take(7)
                        sh """
                            /kaniko/executor \
                                --context="${env.WORKSPACE}" \
                                --dockerfile="${env.WORKSPACE}/${env.PIPELINE_DOCKERFILE}" \
                                --destination="${env.PIPELINE_IMAGE}:${shortCommit}" \
                                --destination="${env.PIPELINE_IMAGE}:latest" \
                                --cache=true \
                                --cache-repo="${env.PIPELINE_IMAGE}-cache"
                        """
                    }
                }
            }
        }

        stage('Build & Push Root Image') {
            when { expression { env.BUILD_ROOT == 'true' } }
            agent { label 'kaniko' }
            steps {
                container('kaniko') {
                    script {
                        def shortCommit = env.GIT_COMMIT.take(7)
                        sh """
                            /kaniko/executor \
                                --context="${env.WORKSPACE}" \
                                --dockerfile="${env.WORKSPACE}/${env.ROOT_DOCKERFILE}" \
                                --destination="${env.ROOT_IMAGE}:${shortCommit}" \
                                --destination="${env.ROOT_IMAGE}:latest" \
                                --cache=true \
                                --cache-repo="${env.ROOT_IMAGE}-cache"
                        """
                    }
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