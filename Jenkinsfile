pipeline {
    agent any
    
    environment {
        DOCKERHUB_USERNAME = "tchaikovsky29"
        ROOT_IMAGE         = "${DOCKERHUB_USERNAME}/env-base-image"
        PIPELINE_IMAGE     = "${DOCKERHUB_USERNAME}/my-app-pipeline"
        GIT_SSL_NO_VERIFY = 'true'
        PIPELINE_DOCKERFILE = "src/pipeline/Dockerfile"
        PIPELINE_TRIGGER    = "src/pipeline/inference_transformer.py"
        ROOT_SRC_DIR        = "src/"
        ROOT_DOCKERFILE     = "Dockerfile"
    }

    stages {
        stage('Checkout') {
            steps {
                sshagent(['Github-ssh']) {
                    checkout([
                        $class: 'GitSCM',
                        branches: [[name: '*/main']],
                        userRemoteConfigs: [[
                            url: 'git@github.com:Tchaikovsky29/Bicycle-Demand-Prediction.git',
                            credentialsId: 'Github-ssh'
                        ]]
                    ])
                }
            }
        }

        stage('Detect Changes') {
            steps {
                sshagent(['Github-ssh']) {
                    script {
                        def changedFiles = sh(
                            script: "git diff --name-only HEAD~1 HEAD",
                            returnStdout: true
                        ).trim().split('\n') as List
                        // rest of your script...
                    }
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
                                --destination="${env.PIPELINE_IMAGE}:latest"
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
                                --destination="${env.ROOT_IMAGE}:latest"
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