pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
        DOCKERHUB_USERNAME    = "${DOCKERHUB_CREDENTIALS_USR}"

        // Image names — adjust to match your DockerHub repo
        ROOT_IMAGE      = "${DOCKERHUB_USERNAME}/env-base-image:latest"
        PIPELINE_IMAGE  = "${DOCKERHUB_USERNAME}/inference-transformer:latest"

        // Files that trigger the pipeline image
        PIPELINE_DOCKERFILE = "src/pipeline/Dockerfile"
        PIPELINE_TRIGGER    = "src/pipeline/inference_transformer.py"

        // Root image: anything under src/ except the two pipeline-specific files
        ROOT_SRC_DIR        = "src/"
        ROOT_DOCKERFILE     = "Dockerfile"
    }

    stages {

        // ── 1. Detect what changed ────────────────────────────────────────────
        stage('Detect Changes') {
            steps {
                script {
                    // Get the list of files changed in the latest commit
                    def changedFiles = sh(
                        script: "git diff --name-only HEAD~1 HEAD",
                        returnStdout: true
                    ).trim().split('\n') as List

                    echo "Changed files:\n${changedFiles.join('\n')}"

                    // ── Pipeline image trigger ────────────────────────────────
                    // Rebuild if inference_transformer.py OR src/pipeline/Dockerfile changed
                    env.BUILD_PIPELINE = changedFiles.any { f ->
                        f == env.PIPELINE_TRIGGER || f == env.PIPELINE_DOCKERFILE
                    } ? 'true' : 'false'

                    // ── Root image trigger ────────────────────────────────────
                    // Rebuild if:
                    //   • root Dockerfile changed, OR
                    //   • any file under src/ changed EXCEPT the two pipeline-specific files
                    def pipelineExcludes = [env.PIPELINE_TRIGGER, env.PIPELINE_DOCKERFILE]

                    env.BUILD_ROOT = changedFiles.any { f ->
                        f == env.ROOT_DOCKERFILE ||
                        (f.startsWith(env.ROOT_SRC_DIR) && !(f in pipelineExcludes))
                    } ? 'true' : 'false'

                    echo "Build pipeline image : ${env.BUILD_PIPELINE}"
                    echo "Build root image     : ${env.BUILD_ROOT}"
                }
            }
        }

        // ── 2. Build & push pipeline image ───────────────────────────────────
        stage('Build & Push Pipeline Image') {
            when { expression { env.BUILD_PIPELINE == 'true' } }
            steps {
                script {
                    def tag = "${env.PIPELINE_IMAGE}:${env.GIT_COMMIT.take(7)}"
                    echo "Building pipeline image → ${tag}"

                    docker.withRegistry('https://index.docker.io/v1/', 'dockerhub-credentials') {
                        def img = docker.build(tag, "-f ${env.PIPELINE_DOCKERFILE} src/pipeline")
                        img.push()
                        img.push('latest')
                    }
                }
            }
        }

        // ── 3. Build & push root image ────────────────────────────────────────
        stage('Build & Push Root Image') {
            when { expression { env.BUILD_ROOT == 'true' } }
            steps {
                script {
                    def tag = "${env.ROOT_IMAGE}:${env.GIT_COMMIT.take(7)}"
                    echo "Building root image → ${tag}"

                    docker.withRegistry('https://index.docker.io/v1/', 'dockerhub-credentials') {
                        def img = docker.build(tag, "-f ${env.ROOT_DOCKERFILE} .")
                        img.push()
                        img.push('latest')
                    }
                }
            }
        }

        // ── 4. Skip notice ────────────────────────────────────────────────────
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