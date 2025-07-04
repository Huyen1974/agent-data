# Pre-Build Report for Huyen1974/agent-data
**Date**: July 04, 2025

## Workflows
- Result: Workflows copied

## Secrets
- Result: DOCKERHUB_PASSWORD	2025-07-04T10:05:18Z
DOCKERHUB_USERNAME	2025-07-04T10:05:11Z
GCP_PROJECT_ID_TEST	2025-06-22T13:46:59Z
GCP_SERVICE_ACCOUNT	2025-07-03T05:35:17Z
GCP_SERVICE_ACCOUNT_EMAIL_TEST	2025-06-22T13:45:37Z
GCP_SERVICE_ACCOUNT_TEST	2025-07-04T10:05:37Z
GCP_WORKLOAD_IDENTITY_PROVIDER	2025-07-03T08:53:24Z
GCP_WORKLOAD_IDENTITY_PROVIDER_TEST	2025-07-04T10:05:43Z
GCP_WORKLOAD_ID_PROVIDER	2025-07-01T08:32:51Z
GH_TOKEN	2025-07-04T10:05:25Z
JWT_SECRET_KEY	2025-07-03T08:53:10Z
OPENAI_API_KEY	2025-07-03T08:53:04Z
PROJECT_ID	2025-07-03T03:54:13Z
PROJECT_ID_TEST	2025-07-04T10:05:31Z
QDRANT_API_KEY	2025-07-03T08:53:07Z
- Test: ============================= test session starts ==============================
platform linux -- Python 3.10.17, pytest-8.3.5, pluggy-1.5.0
rootdir: /app
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.9.0, asyncio-0.26.0
asyncio: mode=auto, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
>>> Collected 485 tests (manifest filtering disabled)
collected 485 items / 485 deselected / 0 selected

=========================== 485 deselected in 4.38s ============================

## Terraform
- Result: [0m[1mdata.google_secret_manager_secret_version.lark_app_secret: Reading...[0m[0m
[0m[1mdata.google_secret_manager_secret_version.github_token: Reading...[0m[0m
[0m[1mmodule.iam.google_project_iam_member.cloudfunctions_invoker_binding: Refreshing state... [id=chatgpt-db-project/roles/cloudfunctions.invoker/serviceAccount:gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com][0m
[0m[1mmodule.iam.google_project_iam_member.secret_accessor_binding: Refreshing state... [id=chatgpt-db-project/roles/secretmanager.secretAccessor/serviceAccount:gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com][0m
[0m[1mmodule.iam.google_project_iam_member.secret_accessor_binding_prod: Refreshing state... [id=github-chatgpt-ggcloud/roles/secretmanager.secretAccessor/serviceAccount:gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com][0m
[0m[1mdata.google_secret_manager_secret_version.lark_access_token: Reading...[0m[0m
[0m[1mmodule.iam.google_project_iam_member.pubsub_publisher_binding: Refreshing state... [id=chatgpt-db-project/roles/pubsub.publisher/serviceAccount:gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com][0m
[0m[1mmodule.iam.google_project_iam_member.storage_object_admin_binding: Refreshing state... [id=chatgpt-db-project/roles/storage.objectAdmin/serviceAccount:gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com][0m
[0m[1mmodule.workflows.google_workflows_workflow.default: Refreshing state... [id=projects/chatgpt-db-project/locations/asia-southeast1/workflows/my-workflow-test][0m
[0m[1mmodule.cloud_run.google_cloud_run_service.default: Refreshing state... [id=locations/asia-southeast1/namespaces/chatgpt-db-project/services/dummy-function-test][0m
[0m[1mmodule.iam.google_project_iam_member.cloud_run_invoker_binding: Refreshing state... [id=chatgpt-db-project/roles/run.invoker/serviceAccount:gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com][0m
[0m[1mmodule.firestore.google_firestore_database.firestore_db: Refreshing state... [id=projects/chatgpt-db-project/databases/test-default][0m
[0m[1mdata.google_secret_manager_secret_version.github_token: Read complete after 1s [id=projects/812872501910/secrets/github-token-sg/versions/1][0m
[0m[1mdata.google_secret_manager_secret_version.openai_api_key: Reading...[0m[0m
[0m[1mdata.google_secret_manager_secret_version.lark_access_token: Read complete after 1s [id=projects/812872501910/secrets/lark-access-token-sg/versions/145][0m
[0m[1mdata.google_secret_manager_secret_version.lark_app_secret: Read complete after 1s [id=projects/812872501910/secrets/lark-app-secret-sg/versions/1][0m
[0m[1mdata.google_secret_manager_secret_version.openai_api_key: Read complete after 1s [id=projects/812872501910/secrets/chatgpt-deployer-key/versions/1][0m

[1m[36mNote:[0m[1m Objects have changed outside of Terraform
[0m
Terraform detected the following changes made outside of Terraform since the
last "terraform apply" which may have affected this plan:

[1m  # module.cloud_run.google_cloud_run_service.default[0m has been deleted
[0m  [31m-[0m[0m resource "google_cloud_run_service" "default" {
        id                         = "locations/asia-southeast1/namespaces/chatgpt-db-project/services/dummy-function-test"
      [31m-[0m[0m name                       = "dummy-function-test" [90m-> null[0m[0m
      [31m-[0m[0m status                     = [
          [31m-[0m[0m {
              [31m-[0m[0m conditions                   = [
                  [31m-[0m[0m {
                      [31m-[0m[0m message = ""
                      [31m-[0m[0m reason  = ""
                      [31m-[0m[0m status  = "True"
                      [31m-[0m[0m type    = "Ready"
                    },
                  [31m-[0m[0m {
                      [31m-[0m[0m message = ""
                      [31m-[0m[0m reason  = ""
                      [31m-[0m[0m status  = "True"
                      [31m-[0m[0m type    = "ConfigurationsReady"
                    },
                  [31m-[0m[0m {
                      [31m-[0m[0m message = ""
                      [31m-[0m[0m reason  = ""
                      [31m-[0m[0m status  = "True"
                      [31m-[0m[0m type    = "RoutesReady"
                    },
                ]
              [31m-[0m[0m latest_created_revision_name = "dummy-function-test-00001-vbc"
              [31m-[0m[0m latest_ready_revision_name   = "dummy-function-test-00001-vbc"
              [31m-[0m[0m observed_generation          = 1
              [31m-[0m[0m traffic                      = [
                  [31m-[0m[0m {
                      [31m-[0m[0m latest_revision = true
                      [31m-[0m[0m percent         = 100
                      [31m-[0m[0m revision_name   = "dummy-function-test-00001-vbc"
                      [31m-[0m[0m tag             = ""
                      [31m-[0m[0m url             = ""
                    },
                ]
              [31m-[0m[0m url                          = "https://dummy-function-test-k4ttla6eeq-as.a.run.app"
            },
        ] [90m-> null[0m[0m
        [90m# (3 unchanged attributes hidden)[0m[0m

        [90m# (3 unchanged blocks hidden)[0m[0m
    }


Unless you have made equivalent changes to your configuration, or ignored the
relevant attributes using ignore_changes, the following plan may include
actions to undo or respond to these changes.
[90m
─────────────────────────────────────────────────────────────────────────────[0m

Terraform used the selected providers to generate the following execution
plan. Resource actions are indicated with the following symbols:
  [32m+[0m create[0m
  [33m~[0m update in-place[0m

Terraform planned the following actions, but then encountered a problem:

[1m  # module.cloud_run.google_cloud_run_service.default[0m will be created
[0m  [32m+[0m[0m resource "google_cloud_run_service" "default" {
      [32m+[0m[0m autogenerate_revision_name = false
      [32m+[0m[0m id                         = (known after apply)
      [32m+[0m[0m location                   = "asia-southeast1"
      [32m+[0m[0m name                       = "dummy-function-test"
      [32m+[0m[0m project                    = "chatgpt-db-project"
      [32m+[0m[0m status                     = (known after apply)

      [32m+[0m[0m template {
          [32m+[0m[0m spec {
              [32m+[0m[0m container_concurrency = (known after apply)
              [32m+[0m[0m service_account_name  = "gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com"
              [32m+[0m[0m serving_state         = (known after apply)
              [32m+[0m[0m timeout_seconds       = (known after apply)

              [32m+[0m[0m containers {
                  [32m+[0m[0m image = "gcr.io/chatgpt-db-project/dummy-function:v1.0.0"
                  [32m+[0m[0m name  = (known after apply)

                  [32m+[0m[0m env {
                      [32m+[0m[0m name  = "ENVIRONMENT"
                      [32m+[0m[0m value = "test"
                    }
                  [32m+[0m[0m env {
                      [32m+[0m[0m name = "GITHUB_TOKEN"

                      [32m+[0m[0m value_from {
                          [32m+[0m[0m secret_key_ref {
                              [32m+[0m[0m key  = "latest"
                              [32m+[0m[0m name = "github-token-sg"
                            }
                        }
                    }
                  [32m+[0m[0m env {
                      [32m+[0m[0m name = "LARK_ACCESS_TOKEN"

                      [32m+[0m[0m value_from {
                          [32m+[0m[0m secret_key_ref {
                              [32m+[0m[0m key  = "latest"
                              [32m+[0m[0m name = "lark-access-token-sg"
                            }
                        }
                    }
                  [32m+[0m[0m env {
                      [32m+[0m[0m name = "LARK_APP_SECRET"

                      [32m+[0m[0m value_from {
                          [32m+[0m[0m secret_key_ref {
                              [32m+[0m[0m key  = "latest"
                              [32m+[0m[0m name = "lark-app-secret-sg"
                            }
                        }
                    }
                  [32m+[0m[0m env {
                      [32m+[0m[0m name = "OPENAI_API_KEY"

                      [32m+[0m[0m value_from {
                          [32m+[0m[0m secret_key_ref {
                              [32m+[0m[0m key  = "latest"
                              [32m+[0m[0m name = "chatgpt-deployer-key"
                            }
                        }
                    }

                  [32m+[0m[0m ports {
                      [32m+[0m[0m container_port = 8080
                      [32m+[0m[0m name           = (known after apply)
                    }
                }
            }
        }
    }

[1m  # module.workflows.google_workflows_workflow.default[0m will be updated in-place
[0m  [33m~[0m[0m resource "google_workflows_workflow" "default" {
      [33m~[0m[0m effective_labels = {
          [31m-[0m[0m "goog-terraform-provisioned" = "true" [90m-> null[0m[0m
        }
        id               = "projects/chatgpt-db-project/locations/asia-southeast1/workflows/my-workflow-test"
        name             = "my-workflow-test"
      [33m~[0m[0m terraform_labels = {
          [31m-[0m[0m "goog-terraform-provisioned" = "true" [90m-> null[0m[0m
        }
        [90m# (10 unchanged attributes hidden)[0m[0m
    }

[1mPlan:[0m 1 to add, 1 to change, 0 to destroy.
[0m[33m╷[0m[0m
[33m│[0m [0m[1m[33mWarning: [0m[0m[1mFailed to decode resource from state[0m
[33m│[0m [0m
[33m│[0m [0m[0mError decoding
[33m│[0m [0m"module.cloud_storage.google_storage_bucket.artifact_storage" from prior
[33m│[0m [0mstate: unsupported attribute "hierarchical_namespace"
[33m╵[0m[0m
[33m╷[0m[0m
[33m│[0m [0m[1m[33mWarning: [0m[0m[1mFailed to decode resource from state[0m
[33m│[0m [0m
[33m│[0m [0m[0mError decoding
[33m│[0m [0m"module.cloud_storage.google_storage_bucket.function_storage" from prior
[33m│[0m [0mstate: unsupported attribute "hierarchical_namespace"
[33m╵[0m[0m
[33m╷[0m[0m
[33m│[0m [0m[1m[33mWarning: [0m[0m[1mFailed to decode resource from state[0m
[33m│[0m [0m
[33m│[0m [0m[0mError decoding "module.cloud_storage.google_storage_bucket.log_storage"
[33m│[0m [0mfrom prior state: unsupported attribute "hierarchical_namespace"
[33m╵[0m[0m
[31m╷[0m[0m
[31m│[0m [0m[1m[31mError: [0m[0m[1mResource instance managed by newer provider version[0m
[31m│[0m [0m
[31m│[0m [0m[0mThe current state of
[31m│[0m [0mmodule.cloud_storage.google_storage_bucket.function_storage was created by
[31m│[0m [0ma newer provider version than is currently selected. Upgrade the google
[31m│[0m [0mprovider to work with this state.
[31m╵[0m[0m
[31m╷[0m[0m
[31m│[0m [0m[1m[31mError: [0m[0m[1mResource instance managed by newer provider version[0m
[31m│[0m [0m
[31m│[0m [0m[0mThe current state of module.cloud_storage.google_storage_bucket.log_storage
[31m│[0m [0mwas created by a newer provider version than is currently selected. Upgrade
[31m│[0m [0mthe google provider to work with this state.
[31m╵[0m[0m
[31m╷[0m[0m
[31m│[0m [0m[1m[31mError: [0m[0m[1mResource instance managed by newer provider version[0m
[31m│[0m [0m
[31m│[0m [0m[0mThe current state of
[31m│[0m [0mmodule.cloud_storage.google_storage_bucket.artifact_storage was created by
[31m│[0m [0ma newer provider version than is currently selected. Upgrade the google
[31m│[0m [0mprovider to work with this state.
[31m╵[0m[0m
Terraform apply had provider version issues but infrastructure mostly exists

## Firestore
- Result: Database test-default created, roles/datastore.user granted

## Dockerfile
- Result: #0 building with "desktop-linux" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 1.25kB done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.10.17-slim
#2 ...

#3 [auth] library/python:pull token for registry-1.docker.io
#3 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.10.17-slim
#2 DONE 4.1s

#4 [internal] load .dockerignore
#4 transferring context: 2B done
#4 DONE 0.0s

#5 [ 1/21] FROM docker.io/library/python:3.10.17-slim@sha256:49454d2bf78a48f217eb25ecbcb4b5face313fea6a6e82706465a6990303ada2
#5 resolve docker.io/library/python:3.10.17-slim@sha256:49454d2bf78a48f217eb25ecbcb4b5face313fea6a6e82706465a6990303ada2 0.0s done
#5 DONE 0.1s

#6 [internal] load build context
#6 transferring context: 220.02MB 2.5s done
#6 DONE 2.5s

#7 [ 2/21] RUN apt-get update && apt-get install -y --no-install-recommends     gcc     g++     build-essential     && rm -rf /var/lib/apt/lists/*
#7 1.233 Get:1 http://deb.debian.org/debian bookworm InRelease [151 kB]
#7 1.421 Get:2 http://deb.debian.org/debian bookworm-updates InRelease [55.4 kB]
#7 1.488 Get:3 http://deb.debian.org/debian-security bookworm-security InRelease [48.0 kB]
#7 1.560 Get:4 http://deb.debian.org/debian bookworm/main arm64 Packages [8693 kB]
#7 4.497 Get:5 http://deb.debian.org/debian bookworm-updates/main arm64 Packages [756 B]
#7 4.499 Get:6 http://deb.debian.org/debian-security bookworm-security/main arm64 Packages [267 kB]
#7 5.212 Fetched 9215 kB in 5s (1923 kB/s)
#7 5.212 Reading package lists...
#7 5.615 Reading package lists...
#7 5.982 Building dependency tree...
#7 6.065 Reading state information...
#7 6.159 The following additional packages will be installed:
#7 6.159   binutils binutils-aarch64-linux-gnu binutils-common bzip2 cpp cpp-12
#7 6.159   dpkg-dev g++-12 gcc-12 libasan8 libatomic1 libbinutils libc-dev-bin
#7 6.159   libc6-dev libcc1-0 libcrypt-dev libctf-nobfd0 libctf0 libdpkg-perl
#7 6.159   libgcc-12-dev libgdbm-compat4 libgomp1 libgprofng0 libhwasan0 libisl23
#7 6.159   libitm1 libjansson4 liblsan0 libmpc3 libmpfr6 libnsl-dev libperl5.36
#7 6.159   libstdc++-12-dev libtirpc-dev libtsan2 libubsan1 linux-libc-dev make patch
#7 6.159   perl perl-modules-5.36 rpcsvc-proto xz-utils
#7 6.160 Suggested packages:
#7 6.160   binutils-doc bzip2-doc cpp-doc gcc-12-locales cpp-12-doc debian-keyring
#7 6.160   gcc-12-doc gcc-multilib manpages-dev autoconf automake libtool flex bison
#7 6.160   gdb gcc-doc glibc-doc gnupg | sq | sqop | pgpainless-cli sensible-utils git
#7 6.160   bzr libstdc++-12-doc make-doc ed diffutils-doc perl-doc
#7 6.160   libterm-readline-gnu-perl | libterm-readline-perl-perl
#7 6.160   libtap-harness-archive-perl
#7 6.160 Recommended packages:
#7 6.160   fakeroot gnupg | sq | sqop | pgpainless-cli libalgorithm-merge-perl manpages
#7 6.160   manpages-dev libc-devtools libfile-fcntllock-perl liblocale-gettext-perl
#7 6.423 The following NEW packages will be installed:
#7 6.423   binutils binutils-aarch64-linux-gnu binutils-common build-essential bzip2
#7 6.423   cpp cpp-12 dpkg-dev g++ g++-12 gcc gcc-12 libasan8 libatomic1 libbinutils
#7 6.423   libc-dev-bin libc6-dev libcc1-0 libcrypt-dev libctf-nobfd0 libctf0
#7 6.423   libdpkg-perl libgcc-12-dev libgdbm-compat4 libgomp1 libgprofng0 libhwasan0
#7 6.423   libisl23 libitm1 libjansson4 liblsan0 libmpc3 libmpfr6 libnsl-dev
#7 6.423   libperl5.36 libstdc++-12-dev libtirpc-dev libtsan2 libubsan1 linux-libc-dev
#7 6.423   make patch perl perl-modules-5.36 rpcsvc-proto xz-utils
#7 6.561 0 upgraded, 46 newly installed, 0 to remove and 3 not upgraded.
#7 6.561 Need to get 66.0 MB of archives.
#7 6.561 After this operation, 297 MB of additional disk space will be used.
#7 6.561 Get:1 http://deb.debian.org/debian bookworm/main arm64 perl-modules-5.36 all 5.36.0-7+deb12u2 [2815 kB]
#7 7.501 Get:2 http://deb.debian.org/debian bookworm/main arm64 libgdbm-compat4 arm64 1.23-3 [48.0 kB]
#7 7.510 Get:3 http://deb.debian.org/debian bookworm/main arm64 libperl5.36 arm64 5.36.0-7+deb12u2 [4027 kB]
#7 8.215 Get:4 http://deb.debian.org/debian bookworm/main arm64 perl arm64 5.36.0-7+deb12u2 [239 kB]
#7 8.275 Get:5 http://deb.debian.org/debian bookworm/main arm64 bzip2 arm64 1.0.8-5+b1 [48.9 kB]
#7 8.425 Get:6 http://deb.debian.org/debian bookworm/main arm64 xz-utils arm64 5.4.1-1 [469 kB]
#7 8.431 Get:7 http://deb.debian.org/debian bookworm/main arm64 binutils-common arm64 2.40-2 [2487 kB]
#7 9.003 Get:8 http://deb.debian.org/debian bookworm/main arm64 libbinutils arm64 2.40-2 [645 kB]
#7 9.193 Get:9 http://deb.debian.org/debian bookworm/main arm64 libctf-nobfd0 arm64 2.40-2 [144 kB]
#7 9.263 Get:10 http://deb.debian.org/debian bookworm/main arm64 libctf0 arm64 2.40-2 [79.2 kB]
#7 9.265 Get:11 http://deb.debian.org/debian bookworm/main arm64 libgprofng0 arm64 2.40-2 [680 kB]
#7 9.580 Get:12 http://deb.debian.org/debian bookworm/main arm64 libjansson4 arm64 2.14-2 [40.2 kB]
#7 9.619 Get:13 http://deb.debian.org/debian bookworm/main arm64 binutils-aarch64-linux-gnu arm64 2.40-2 [2637 kB]
#7 10.90 Get:14 http://deb.debian.org/debian bookworm/main arm64 binutils arm64 2.40-2 [64.9 kB]
#7 10.92 Get:15 http://deb.debian.org/debian bookworm/main arm64 libc-dev-bin arm64 2.36-9+deb12u10 [46.2 kB]
#7 10.96 Get:16 http://deb.debian.org/debian-security bookworm-security/main arm64 linux-libc-dev arm64 6.1.140-1 [2120 kB]
#7 12.83 Get:17 http://deb.debian.org/debian bookworm/main arm64 libcrypt-dev arm64 1:4.4.33-2 [121 kB]
#7 12.97 Get:18 http://deb.debian.org/debian bookworm/main arm64 libtirpc-dev arm64 1.3.3+ds-1 [194 kB]
#7 13.21 Get:19 http://deb.debian.org/debian bookworm/main arm64 libnsl-dev arm64 1.3.0-2 [66.1 kB]
#7 13.28 Get:20 http://deb.debian.org/debian bookworm/main arm64 rpcsvc-proto arm64 1.4.3-1 [59.7 kB]
#7 13.34 Get:21 http://deb.debian.org/debian bookworm/main arm64 libc6-dev arm64 2.36-9+deb12u10 [1431 kB]
#7 14.63 Get:22 http://deb.debian.org/debian bookworm/main arm64 libisl23 arm64 0.25-1.1 [610 kB]
#7 15.10 Get:23 http://deb.debian.org/debian bookworm/main arm64 libmpfr6 arm64 4.2.0-1 [600 kB]
#7 15.52 Get:24 http://deb.debian.org/debian bookworm/main arm64 libmpc3 arm64 1.3.1-1 [49.2 kB]
#7 15.55 Get:25 http://deb.debian.org/debian bookworm/main arm64 cpp-12 arm64 12.2.0-14+deb12u1 [8228 kB]
#7 21.35 Get:26 http://deb.debian.org/debian bookworm/main arm64 cpp arm64 4:12.2.0-3 [6832 B]
#7 21.35 Get:27 http://deb.debian.org/debian bookworm/main arm64 libcc1-0 arm64 12.2.0-14+deb12u1 [37.7 kB]
#7 21.40 Get:28 http://deb.debian.org/debian bookworm/main arm64 libgomp1 arm64 12.2.0-14+deb12u1 [104 kB]
#7 21.47 Get:29 http://deb.debian.org/debian bookworm/main arm64 libitm1 arm64 12.2.0-14+deb12u1 [24.0 kB]
#7 21.47 Get:30 http://deb.debian.org/debian bookworm/main arm64 libatomic1 arm64 12.2.0-14+deb12u1 [9568 B]
#7 21.48 Get:31 http://deb.debian.org/debian bookworm/main arm64 libasan8 arm64 12.2.0-14+deb12u1 [2096 kB]
#7 22.72 Get:32 http://deb.debian.org/debian bookworm/main arm64 liblsan0 arm64 12.2.0-14+deb12u1 [926 kB]
#7 23.27 Get:33 http://deb.debian.org/debian bookworm/main arm64 libtsan2 arm64 12.2.0-14+deb12u1 [2178 kB]
#7 24.53 Get:34 http://deb.debian.org/debian bookworm/main arm64 libubsan1 arm64 12.2.0-14+deb12u1 [862 kB]
#7 25.14 Get:35 http://deb.debian.org/debian bookworm/main arm64 libhwasan0 arm64 12.2.0-14+deb12u1 [999 kB]
#7 25.63 Get:36 http://deb.debian.org/debian bookworm/main arm64 libgcc-12-dev arm64 12.2.0-14+deb12u1 [956 kB]
#7 26.16 Get:37 http://deb.debian.org/debian bookworm/main arm64 gcc-12 arm64 12.2.0-14+deb12u1 [16.3 MB]
#7 58.09 Get:38 http://deb.debian.org/debian bookworm/main arm64 gcc arm64 4:12.2.0-3 [5244 B]
#7 58.11 Get:39 http://deb.debian.org/debian bookworm/main arm64 libstdc++-12-dev arm64 12.2.0-14+deb12u1 [2007 kB]
#7 66.42 Get:40 http://deb.debian.org/debian bookworm/main arm64 g++-12 arm64 12.2.0-14+deb12u1 [9072 kB]
#7 92.67 Get:41 http://deb.debian.org/debian bookworm/main arm64 g++ arm64 4:12.2.0-3 [1336 B]
#7 92.68 Get:42 http://deb.debian.org/debian bookworm/main arm64 make arm64 4.3-4.1 [391 kB]
#7 94.00 Get:43 http://deb.debian.org/debian bookworm/main arm64 libdpkg-perl all 1.21.22 [603 kB]
#7 96.35 Get:44 http://deb.debian.org/debian bookworm/main arm64 patch arm64 2.7.6-7 [121 kB]
#7 96.67 Get:45 http://deb.debian.org/debian bookworm/main arm64 dpkg-dev all 1.21.22 [1353 kB]
#7 99.62 Get:46 http://deb.debian.org/debian bookworm/main arm64 build-essential arm64 12.9 [7704 B]
#7 99.79 debconf: delaying package configuration, since apt-utils is not installed
#7 99.81 Fetched 66.0 MB in 1min 33s (708 kB/s)
#7 99.82 Selecting previously unselected package perl-modules-5.36.
#7 99.82 (Reading database ... (Reading database ... 5%(Reading database ... 10%(Reading database ... 15%(Reading database ... 20%(Reading database ... 25%(Reading database ... 30%(Reading database ... 35%(Reading database ... 40%(Reading database ... 45%(Reading database ... 50%(Reading database ... 55%(Reading database ... 60%(Reading database ... 65%(Reading database ... 70%(Reading database ... 75%(Reading database ... 80%(Reading database ... 85%(Reading database ... 90%(Reading database ... 95%(Reading database ... 100%(Reading database ... 6680 files and directories currently installed.)
#7 99.84 Preparing to unpack .../00-perl-modules-5.36_5.36.0-7+deb12u2_all.deb ...
#7 99.84 Unpacking perl-modules-5.36 (5.36.0-7+deb12u2) ...
#7 100.1 Selecting previously unselected package libgdbm-compat4:arm64.
#7 100.1 Preparing to unpack .../01-libgdbm-compat4_1.23-3_arm64.deb ...
#7 100.1 Unpacking libgdbm-compat4:arm64 (1.23-3) ...
#7 100.1 Selecting previously unselected package libperl5.36:arm64.
#7 100.1 Preparing to unpack .../02-libperl5.36_5.36.0-7+deb12u2_arm64.deb ...
#7 100.1 Unpacking libperl5.36:arm64 (5.36.0-7+deb12u2) ...
#7 100.3 Selecting previously unselected package perl.
#7 100.3 Preparing to unpack .../03-perl_5.36.0-7+deb12u2_arm64.deb ...
#7 100.3 Unpacking perl (5.36.0-7+deb12u2) ...
#7 100.4 Selecting previously unselected package bzip2.
#7 100.4 Preparing to unpack .../04-bzip2_1.0.8-5+b1_arm64.deb ...
#7 100.4 Unpacking bzip2 (1.0.8-5+b1) ...
#7 100.4 Selecting previously unselected package xz-utils.
#7 100.4 Preparing to unpack .../05-xz-utils_5.4.1-1_arm64.deb ...
#7 100.4 Unpacking xz-utils (5.4.1-1) ...
#7 100.4 Selecting previously unselected package binutils-common:arm64.
#7 100.4 Preparing to unpack .../06-binutils-common_2.40-2_arm64.deb ...
#7 100.4 Unpacking binutils-common:arm64 (2.40-2) ...
#7 100.6 Selecting previously unselected package libbinutils:arm64.
#7 100.6 Preparing to unpack .../07-libbinutils_2.40-2_arm64.deb ...
#7 100.6 Unpacking libbinutils:arm64 (2.40-2) ...
#7 100.6 Selecting previously unselected package libctf-nobfd0:arm64.
#7 100.6 Preparing to unpack .../08-libctf-nobfd0_2.40-2_arm64.deb ...
#7 100.6 Unpacking libctf-nobfd0:arm64 (2.40-2) ...
#7 100.6 Selecting previously unselected package libctf0:arm64.
#7 100.6 Preparing to unpack .../09-libctf0_2.40-2_arm64.deb ...
#7 100.6 Unpacking libctf0:arm64 (2.40-2) ...
#7 100.7 Selecting previously unselected package libgprofng0:arm64.
#7 100.7 Preparing to unpack .../10-libgprofng0_2.40-2_arm64.deb ...
#7 100.7 Unpacking libgprofng0:arm64 (2.40-2) ...
#7 100.7 Selecting previously unselected package libjansson4:arm64.
#7 100.7 Preparing to unpack .../11-libjansson4_2.14-2_arm64.deb ...
#7 100.7 Unpacking libjansson4:arm64 (2.14-2) ...
#7 100.7 Selecting previously unselected package binutils-aarch64-linux-gnu.
#7 100.7 Preparing to unpack .../12-binutils-aarch64-linux-gnu_2.40-2_arm64.deb ...
#7 100.7 Unpacking binutils-aarch64-linux-gnu (2.40-2) ...
#7 100.9 Selecting previously unselected package binutils.
#7 100.9 Preparing to unpack .../13-binutils_2.40-2_arm64.deb ...
#7 100.9 Unpacking binutils (2.40-2) ...
#7 100.9 Selecting previously unselected package libc-dev-bin.
#7 100.9 Preparing to unpack .../14-libc-dev-bin_2.36-9+deb12u10_arm64.deb ...
#7 100.9 Unpacking libc-dev-bin (2.36-9+deb12u10) ...
#7 101.0 Selecting previously unselected package linux-libc-dev:arm64.
#7 101.0 Preparing to unpack .../15-linux-libc-dev_6.1.140-1_arm64.deb ...
#7 101.0 Unpacking linux-libc-dev:arm64 (6.1.140-1) ...
#7 101.0 Selecting previously unselected package libcrypt-dev:arm64.
#7 101.0 Preparing to unpack .../16-libcrypt-dev_1%3a4.4.33-2_arm64.deb ...
#7 101.1 Unpacking libcrypt-dev:arm64 (1:4.4.33-2) ...
#7 101.1 Selecting previously unselected package libtirpc-dev:arm64.
#7 101.1 Preparing to unpack .../17-libtirpc-dev_1.3.3+ds-1_arm64.deb ...
#7 101.1 Unpacking libtirpc-dev:arm64 (1.3.3+ds-1) ...
#7 101.1 Selecting previously unselected package libnsl-dev:arm64.
#7 101.1 Preparing to unpack .../18-libnsl-dev_1.3.0-2_arm64.deb ...
#7 101.1 Unpacking libnsl-dev:arm64 (1.3.0-2) ...
#7 101.1 Selecting previously unselected package rpcsvc-proto.
#7 101.1 Preparing to unpack .../19-rpcsvc-proto_1.4.3-1_arm64.deb ...
#7 101.1 Unpacking rpcsvc-proto (1.4.3-1) ...
#7 101.1 Selecting previously unselected package libc6-dev:arm64.
#7 101.1 Preparing to unpack .../20-libc6-dev_2.36-9+deb12u10_arm64.deb ...
#7 101.1 Unpacking libc6-dev:arm64 (2.36-9+deb12u10) ...
#7 101.2 Selecting previously unselected package libisl23:arm64.
#7 101.2 Preparing to unpack .../21-libisl23_0.25-1.1_arm64.deb ...
#7 101.2 Unpacking libisl23:arm64 (0.25-1.1) ...
#7 101.3 Selecting previously unselected package libmpfr6:arm64.
#7 101.3 Preparing to unpack .../22-libmpfr6_4.2.0-1_arm64.deb ...
#7 101.3 Unpacking libmpfr6:arm64 (4.2.0-1) ...
#7 101.3 Selecting previously unselected package libmpc3:arm64.
#7 101.3 Preparing to unpack .../23-libmpc3_1.3.1-1_arm64.deb ...
#7 101.3 Unpacking libmpc3:arm64 (1.3.1-1) ...
#7 101.3 Selecting previously unselected package cpp-12.
#7 101.3 Preparing to unpack .../24-cpp-12_12.2.0-14+deb12u1_arm64.deb ...
#7 101.3 Unpacking cpp-12 (12.2.0-14+deb12u1) ...
#7 101.8 Selecting previously unselected package cpp.
#7 101.8 Preparing to unpack .../25-cpp_4%3a12.2.0-3_arm64.deb ...
#7 101.8 Unpacking cpp (4:12.2.0-3) ...
#7 101.8 Selecting previously unselected package libcc1-0:arm64.
#7 101.8 Preparing to unpack .../26-libcc1-0_12.2.0-14+deb12u1_arm64.deb ...
#7 101.9 Unpacking libcc1-0:arm64 (12.2.0-14+deb12u1) ...
#7 101.9 Selecting previously unselected package libgomp1:arm64.
#7 101.9 Preparing to unpack .../27-libgomp1_12.2.0-14+deb12u1_arm64.deb ...
#7 101.9 Unpacking libgomp1:arm64 (12.2.0-14+deb12u1) ...
#7 101.9 Selecting previously unselected package libitm1:arm64.
#7 101.9 Preparing to unpack .../28-libitm1_12.2.0-14+deb12u1_arm64.deb ...
#7 101.9 Unpacking libitm1:arm64 (12.2.0-14+deb12u1) ...
#7 101.9 Selecting previously unselected package libatomic1:arm64.
#7 101.9 Preparing to unpack .../29-libatomic1_12.2.0-14+deb12u1_arm64.deb ...
#7 101.9 Unpacking libatomic1:arm64 (12.2.0-14+deb12u1) ...
#7 101.9 Selecting previously unselected package libasan8:arm64.
#7 101.9 Preparing to unpack .../30-libasan8_12.2.0-14+deb12u1_arm64.deb ...
#7 101.9 Unpacking libasan8:arm64 (12.2.0-14+deb12u1) ...
#7 102.0 Selecting previously unselected package liblsan0:arm64.
#7 102.1 Preparing to unpack .../31-liblsan0_12.2.0-14+deb12u1_arm64.deb ...
#7 102.1 Unpacking liblsan0:arm64 (12.2.0-14+deb12u1) ...
#7 102.1 Selecting previously unselected package libtsan2:arm64.
#7 102.1 Preparing to unpack .../32-libtsan2_12.2.0-14+deb12u1_arm64.deb ...
#7 102.1 Unpacking libtsan2:arm64 (12.2.0-14+deb12u1) ...
#7 102.2 Selecting previously unselected package libubsan1:arm64.
#7 102.2 Preparing to unpack .../33-libubsan1_12.2.0-14+deb12u1_arm64.deb ...
#7 102.2 Unpacking libubsan1:arm64 (12.2.0-14+deb12u1) ...
#7 102.3 Selecting previously unselected package libhwasan0:arm64.
#7 102.3 Preparing to unpack .../34-libhwasan0_12.2.0-14+deb12u1_arm64.deb ...
#7 102.3 Unpacking libhwasan0:arm64 (12.2.0-14+deb12u1) ...
#7 102.4 Selecting previously unselected package libgcc-12-dev:arm64.
#7 102.4 Preparing to unpack .../35-libgcc-12-dev_12.2.0-14+deb12u1_arm64.deb ...
#7 102.4 Unpacking libgcc-12-dev:arm64 (12.2.0-14+deb12u1) ...
#7 102.5 Selecting previously unselected package gcc-12.
#7 102.5 Preparing to unpack .../36-gcc-12_12.2.0-14+deb12u1_arm64.deb ...
#7 102.5 Unpacking gcc-12 (12.2.0-14+deb12u1) ...
#7 103.0 Selecting previously unselected package gcc.
#7 103.0 Preparing to unpack .../37-gcc_4%3a12.2.0-3_arm64.deb ...
#7 103.0 Unpacking gcc (4:12.2.0-3) ...
#7 103.0 Selecting previously unselected package libstdc++-12-dev:arm64.
#7 103.0 Preparing to unpack .../38-libstdc++-12-dev_12.2.0-14+deb12u1_arm64.deb ...
#7 103.0 Unpacking libstdc++-12-dev:arm64 (12.2.0-14+deb12u1) ...
#7 103.1 Selecting previously unselected package g++-12.
#7 103.1 Preparing to unpack .../39-g++-12_12.2.0-14+deb12u1_arm64.deb ...
#7 103.1 Unpacking g++-12 (12.2.0-14+deb12u1) ...
#7 103.5 Selecting previously unselected package g++.
#7 103.5 Preparing to unpack .../40-g++_4%3a12.2.0-3_arm64.deb ...
#7 103.5 Unpacking g++ (4:12.2.0-3) ...
#7 103.5 Selecting previously unselected package make.
#7 103.6 Preparing to unpack .../41-make_4.3-4.1_arm64.deb ...
#7 103.6 Unpacking make (4.3-4.1) ...
#7 103.6 Selecting previously unselected package libdpkg-perl.
#7 103.6 Preparing to unpack .../42-libdpkg-perl_1.21.22_all.deb ...
#7 103.6 Unpacking libdpkg-perl (1.21.22) ...
#7 103.6 Selecting previously unselected package patch.
#7 103.6 Preparing to unpack .../43-patch_2.7.6-7_arm64.deb ...
#7 103.6 Unpacking patch (2.7.6-7) ...
#7 103.6 Selecting previously unselected package dpkg-dev.
#7 103.6 Preparing to unpack .../44-dpkg-dev_1.21.22_all.deb ...
#7 103.6 Unpacking dpkg-dev (1.21.22) ...
#7 103.7 Selecting previously unselected package build-essential.
#7 103.7 Preparing to unpack .../45-build-essential_12.9_arm64.deb ...
#7 103.7 Unpacking build-essential (12.9) ...
#7 103.7 Setting up binutils-common:arm64 (2.40-2) ...
#7 103.7 Setting up linux-libc-dev:arm64 (6.1.140-1) ...
#7 103.7 Setting up libctf-nobfd0:arm64 (2.40-2) ...
#7 103.7 Setting up libgomp1:arm64 (12.2.0-14+deb12u1) ...
#7 103.7 Setting up bzip2 (1.0.8-5+b1) ...
#7 103.8 Setting up libjansson4:arm64 (2.14-2) ...
#7 103.8 Setting up perl-modules-5.36 (5.36.0-7+deb12u2) ...
#7 103.8 Setting up libtirpc-dev:arm64 (1.3.3+ds-1) ...
#7 103.8 Setting up rpcsvc-proto (1.4.3-1) ...
#7 103.8 Setting up make (4.3-4.1) ...
#7 103.8 Setting up libmpfr6:arm64 (4.2.0-1) ...
#7 103.8 Setting up xz-utils (5.4.1-1) ...
#7 103.8 update-alternatives: using /usr/bin/xz to provide /usr/bin/lzma (lzma) in auto mode
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/lzma.1.gz because associated file /usr/share/man/man1/xz.1.gz (of link group lzma) doesn't exist
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/unlzma.1.gz because associated file /usr/share/man/man1/unxz.1.gz (of link group lzma) doesn't exist
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/lzcat.1.gz because associated file /usr/share/man/man1/xzcat.1.gz (of link group lzma) doesn't exist
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/lzmore.1.gz because associated file /usr/share/man/man1/xzmore.1.gz (of link group lzma) doesn't exist
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/lzless.1.gz because associated file /usr/share/man/man1/xzless.1.gz (of link group lzma) doesn't exist
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/lzdiff.1.gz because associated file /usr/share/man/man1/xzdiff.1.gz (of link group lzma) doesn't exist
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/lzcmp.1.gz because associated file /usr/share/man/man1/xzcmp.1.gz (of link group lzma) doesn't exist
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/lzgrep.1.gz because associated file /usr/share/man/man1/xzgrep.1.gz (of link group lzma) doesn't exist
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/lzegrep.1.gz because associated file /usr/share/man/man1/xzegrep.1.gz (of link group lzma) doesn't exist
#7 103.8 update-alternatives: warning: skip creation of /usr/share/man/man1/lzfgrep.1.gz because associated file /usr/share/man/man1/xzfgrep.1.gz (of link group lzma) doesn't exist
#7 103.8 Setting up libmpc3:arm64 (1.3.1-1) ...
#7 103.8 Setting up libatomic1:arm64 (12.2.0-14+deb12u1) ...
#7 103.8 Setting up patch (2.7.6-7) ...
#7 103.8 Setting up libgdbm-compat4:arm64 (1.23-3) ...
#7 103.8 Setting up libubsan1:arm64 (12.2.0-14+deb12u1) ...
#7 103.8 Setting up libnsl-dev:arm64 (1.3.0-2) ...
#7 103.8 Setting up libhwasan0:arm64 (12.2.0-14+deb12u1) ...
#7 103.8 Setting up libcrypt-dev:arm64 (1:4.4.33-2) ...
#7 103.8 Setting up libasan8:arm64 (12.2.0-14+deb12u1) ...
#7 103.8 Setting up libtsan2:arm64 (12.2.0-14+deb12u1) ...
#7 103.8 Setting up libbinutils:arm64 (2.40-2) ...
#7 103.8 Setting up libisl23:arm64 (0.25-1.1) ...
#7 103.8 Setting up libc-dev-bin (2.36-9+deb12u10) ...
#7 103.8 Setting up libcc1-0:arm64 (12.2.0-14+deb12u1) ...
#7 103.8 Setting up libperl5.36:arm64 (5.36.0-7+deb12u2) ...
#7 103.9 Setting up liblsan0:arm64 (12.2.0-14+deb12u1) ...
#7 103.9 Setting up libitm1:arm64 (12.2.0-14+deb12u1) ...
#7 103.9 Setting up libctf0:arm64 (2.40-2) ...
#7 103.9 Setting up cpp-12 (12.2.0-14+deb12u1) ...
#7 103.9 Setting up perl (5.36.0-7+deb12u2) ...
#7 103.9 Setting up libgprofng0:arm64 (2.40-2) ...
#7 103.9 Setting up libgcc-12-dev:arm64 (12.2.0-14+deb12u1) ...
#7 103.9 Setting up libdpkg-perl (1.21.22) ...
#7 103.9 Setting up cpp (4:12.2.0-3) ...
#7 103.9 Setting up libc6-dev:arm64 (2.36-9+deb12u10) ...
#7 103.9 Setting up libstdc++-12-dev:arm64 (12.2.0-14+deb12u1) ...
#7 103.9 Setting up binutils-aarch64-linux-gnu (2.40-2) ...
#7 103.9 Setting up binutils (2.40-2) ...
#7 103.9 Setting up dpkg-dev (1.21.22) ...
#7 103.9 Setting up gcc-12 (12.2.0-14+deb12u1) ...
#7 103.9 Setting up g++-12 (12.2.0-14+deb12u1) ...
#7 103.9 Setting up gcc (4:12.2.0-3) ...
#7 103.9 Setting up g++ (4:12.2.0-3) ...
#7 103.9 update-alternatives: using /usr/bin/g++ to provide /usr/bin/c++ (c++) in auto mode
#7 103.9 Setting up build-essential (12.9) ...
#7 103.9 Processing triggers for libc-bin (2.36-9+deb12u10) ...
#7 DONE 104.3s

#8 [ 3/21] WORKDIR /app
#8 DONE 0.1s

#9 [ 4/21] COPY requirements.txt .
#9 DONE 0.0s

#10 [ 5/21] RUN pip install --no-cache-dir --timeout=600 -r requirements.txt
#10 1.325 Collecting annotated-types==0.7.0
#10 2.567   Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
#10 2.687 Collecting anyio==4.9.0
#10 2.739   Downloading anyio-4.9.0-py3-none-any.whl (100 kB)
#10 2.816      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100.9/100.9 kB 1.4 MB/s eta 0:00:00
#10 2.904 Collecting Authlib==1.5.2
#10 2.967   Downloading authlib-1.5.2-py2.py3-none-any.whl (232 kB)
#10 3.058      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 232.1/232.1 kB 2.7 MB/s eta 0:00:00
#10 3.160 Collecting cachetools==5.5.2
#10 3.221   Downloading cachetools-5.5.2-py3-none-any.whl (10 kB)
#10 3.363 Collecting certifi==2025.4.26
#10 3.421   Downloading certifi-2025.4.26-py3-none-any.whl (159 kB)
#10 3.483      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 159.6/159.6 kB 2.7 MB/s eta 0:00:00
#10 3.831 Collecting cffi==1.17.1
#10 3.881   Downloading cffi-1.17.1-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (448 kB)
#10 4.295      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 448.2/448.2 kB 1.1 MB/s eta 0:00:00
#10 4.517 Collecting charset-normalizer==3.4.1
#10 4.570   Downloading charset_normalizer-3.4.1-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (141 kB)
#10 4.762      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 141.3/141.3 kB 1.0 MB/s eta 0:00:00
#10 4.864 Collecting click==8.1.8
#10 4.961   Downloading click-8.1.8-py3-none-any.whl (98 kB)
#10 5.051      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 98.2/98.2 kB 1.0 MB/s eta 0:00:00
#10 5.291 Collecting contourpy==1.3.2
#10 5.347   Downloading contourpy-1.3.2-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (312 kB)
#10 5.666      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 312.1/312.1 kB 1.0 MB/s eta 0:00:00
#10 6.113 Collecting cryptography==44.0.2
#10 6.164   Downloading cryptography-44.0.2-cp39-abi3-manylinux_2_34_aarch64.whl (4.0 MB)
#10 13.94      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.0/4.0 MB 509.7 kB/s eta 0:00:00
#10 14.05 Collecting cycler==0.12.1
#10 14.11   Downloading cycler-0.12.1-py3-none-any.whl (8.3 kB)
#10 14.22 Collecting Deprecated==1.2.18
#10 14.28   Downloading Deprecated-1.2.18-py2.py3-none-any.whl (10.0 kB)
#10 14.35 Collecting distro==1.9.0
#10 14.41   Downloading distro-1.9.0-py3-none-any.whl (20 kB)
#10 14.51 Collecting docstring_parser==0.16
#10 14.57   Downloading docstring_parser-0.16-py3-none-any.whl (36 kB)
#10 14.69 Collecting exceptiongroup==1.2.2
#10 14.75   Downloading exceptiongroup-1.2.2-py3-none-any.whl (16 kB)
#10 14.95 Collecting faiss-cpu==1.11.0
#10 15.03   Downloading faiss_cpu-1.11.0-cp310-cp310-manylinux_2_28_aarch64.whl (3.8 MB)
#10 27.75      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.8/3.8 MB 296.6 kB/s eta 0:00:00
#10 27.95 Collecting fastapi==0.115.12
#10 28.01   Downloading fastapi-0.115.12-py3-none-any.whl (95 kB)
#10 28.39      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 95.2/95.2 kB 268.4 kB/s eta 0:00:00
#10 28.51 Collecting Flask<3.0,>=2.3
#10 28.56   Downloading flask-2.3.3-py3-none-any.whl (96 kB)
#10 28.90      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.1/96.1 kB 322.7 kB/s eta 0:00:00
#10 29.28 Collecting fonttools==4.57.0
#10 29.34   Downloading fonttools-4.57.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (4.6 MB)
#10 37.45      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.6/4.6 MB 564.9 kB/s eta 0:00:00
#10 37.57 Collecting freezegun==1.5.1
#10 37.63   Downloading freezegun-1.5.1-py3-none-any.whl (17 kB)
#10 37.74 Collecting google-adk==0.3.0
#10 37.80   Downloading google_adk-0.3.0-py3-none-any.whl (1.2 MB)
#10 39.41      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 731.2 kB/s eta 0:00:00
#10 39.57 Collecting google-api-core==2.24.2
#10 39.65   Downloading google_api_core-2.24.2-py3-none-any.whl (160 kB)
#10 39.96      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 160.1/160.1 kB 484.7 kB/s eta 0:00:00
#10 40.14 Collecting google-api-python-client==2.168.0
#10 40.19   Downloading google_api_python_client-2.168.0-py3-none-any.whl (13.3 MB)
#10 57.60      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 13.3/13.3 MB 728.8 kB/s eta 0:00:00
#10 58.00 Collecting google-auth==2.39.0
#10 58.06   Downloading google_auth-2.39.0-py2.py3-none-any.whl (212 kB)
#10 58.58      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 212.3/212.3 kB 421.2 kB/s eta 0:00:00
#10 58.66 Collecting google-auth-httplib2==0.2.0
#10 58.72   Downloading google_auth_httplib2-0.2.0-py2.py3-none-any.whl (9.3 kB)
#10 58.89 Collecting google-cloud-aiplatform==1.90.0
#10 58.97   Downloading google_cloud_aiplatform-1.90.0-py2.py3-none-any.whl (7.6 MB)
#10 69.85      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 7.6/7.6 MB 697.9 kB/s eta 0:00:00
#10 70.06 Collecting google-cloud-bigquery==3.31.0
#10 70.11   Downloading google_cloud_bigquery-3.31.0-py3-none-any.whl (250 kB)
#10 70.31      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 250.1/250.1 kB 1.3 MB/s eta 0:00:00
#10 70.42 Collecting google-cloud-core==2.4.3
#10 70.47   Downloading google_cloud_core-2.4.3-py2.py3-none-any.whl (29 kB)
#10 70.61 Collecting google-cloud-firestore<2.21.0,>=2.20.2
#10 70.66   Downloading google_cloud_firestore-2.20.2-py3-none-any.whl (358 kB)
#10 70.91      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 358.9/358.9 kB 1.5 MB/s eta 0:00:00
#10 71.02 Collecting google-cloud-resource-manager==1.14.2
#10 71.07   Downloading google_cloud_resource_manager-1.14.2-py3-none-any.whl (394 kB)
#10 71.34      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 394.3/394.3 kB 1.5 MB/s eta 0:00:00
#10 71.45 Collecting google-cloud-secret-manager==2.23.3
#10 71.52   Downloading google_cloud_secret_manager-2.23.3-py3-none-any.whl (217 kB)
#10 71.68      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 217.1/217.1 kB 1.3 MB/s eta 0:00:00
#10 71.82 Collecting google-cloud-speech==2.32.0
#10 71.87   Downloading google_cloud_speech-2.32.0-py3-none-any.whl (334 kB)
#10 72.09      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 334.1/334.1 kB 1.6 MB/s eta 0:00:00
#10 72.23 Collecting google-cloud-storage==2.19.0
#10 72.29   Downloading google_cloud_storage-2.19.0-py2.py3-none-any.whl (131 kB)
#10 72.37      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 131.8/131.8 kB 1.6 MB/s eta 0:00:00
#10 72.48 Collecting google-cloud-trace==1.16.1
#10 72.54   Downloading google_cloud_trace-1.16.1-py3-none-any.whl (103 kB)
#10 72.60      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 103.3/103.3 kB 1.6 MB/s eta 0:00:00
#10 72.79 Collecting google-crc32c==1.7.1
#10 72.86   Downloading google_crc32c-1.7.1-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (33 kB)
#10 72.95 Collecting google-genai==1.12.1
#10 73.01   Downloading google_genai-1.12.1-py3-none-any.whl (165 kB)
#10 73.12      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 165.9/165.9 kB 1.7 MB/s eta 0:00:00
#10 73.23 Collecting google-resumable-media==2.7.2
#10 73.29   Downloading google_resumable_media-2.7.2-py2.py3-none-any.whl (81 kB)
#10 73.33      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 81.3/81.3 kB 2.1 MB/s eta 0:00:00
#10 73.43 Collecting googleapis-common-protos==1.70.0
#10 73.48   Downloading googleapis_common_protos-1.70.0-py3-none-any.whl (294 kB)
#10 73.66      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 294.5/294.5 kB 1.7 MB/s eta 0:00:00
#10 73.77 Collecting graphviz==0.20.3
#10 73.82   Downloading graphviz-0.20.3-py3-none-any.whl (47 kB)
#10 73.84      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47.1/47.1 kB 2.9 MB/s eta 0:00:00
#10 73.92 Collecting grpc-google-iam-v1==0.14.2
#10 73.98   Downloading grpc_google_iam_v1-0.14.2-py3-none-any.whl (19 kB)
#10 75.36 Collecting grpcio==1.68.0
#10 75.42   Downloading grpcio-1.68.0-cp310-cp310-manylinux_2_17_aarch64.whl (5.7 MB)
#10 78.99      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5.7/5.7 MB 1.6 MB/s eta 0:00:00
#10 79.15 Collecting grpcio-status==1.68.0
#10 79.23   Downloading grpcio_status-1.68.0-py3-none-any.whl (14 kB)
#10 79.30 Collecting h11==0.16.0
#10 79.35   Downloading h11-0.16.0-py3-none-any.whl (37 kB)
#10 79.48 Collecting httpcore==1.0.9
#10 79.54   Downloading httpcore-1.0.9-py3-none-any.whl (78 kB)
#10 79.59      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.8/78.8 kB 1.6 MB/s eta 0:00:00
#10 79.68 Collecting httplib2==0.22.0
#10 79.77   Downloading httplib2-0.22.0-py3-none-any.whl (96 kB)
#10 79.83      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 96.9/96.9 kB 1.6 MB/s eta 0:00:00
#10 79.98 Collecting httptools==0.6.4
#10 80.03   Downloading httptools-0.6.4-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (443 kB)
#10 80.33      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 443.1/443.1 kB 1.5 MB/s eta 0:00:00
#10 80.44 Collecting httpx==0.28.1
#10 80.49   Downloading httpx-0.28.1-py3-none-any.whl (73 kB)
#10 80.55      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.5/73.5 kB 1.3 MB/s eta 0:00:00
#10 80.63 Collecting httpx-sse==0.4.0
#10 80.68   Downloading httpx_sse-0.4.0-py3-none-any.whl (7.8 kB)
#10 80.77 Collecting idna==3.10
#10 80.84   Downloading idna-3.10-py3-none-any.whl (70 kB)
#10 80.96      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 70.4/70.4 kB 3.3 MB/s eta 0:00:00
#10 81.11 Collecting importlib_metadata==8.6.1
#10 81.17   Downloading importlib_metadata-8.6.1-py3-none-any.whl (26 kB)
#10 81.26 Collecting iniconfig==2.1.0
#10 81.36   Downloading iniconfig-2.1.0-py3-none-any.whl (6.0 kB)
#10 81.80 Collecting jiter==0.9.0
#10 81.88   Downloading jiter-0.9.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (341 kB)
#10 82.44      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 341.7/341.7 kB 612.0 kB/s eta 0:00:00
#10 83.23 Collecting joblib==1.4.2
#10 83.29   Downloading joblib-1.4.2-py3-none-any.whl (301 kB)
#10 83.83      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 301.8/301.8 kB 554.0 kB/s eta 0:00:00
#10 84.13 Collecting kiwisolver==1.4.8
#10 84.19   Downloading kiwisolver-1.4.8-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.4 MB)
#10 85.92      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.4/1.4 MB 817.2 kB/s eta 0:00:00
#10 86.56 Collecting matplotlib==3.10.1
#10 86.63   Downloading matplotlib-3.10.1-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (8.4 MB)
#10 96.09      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8.4/8.4 MB 893.0 kB/s eta 0:00:00
#10 96.22 Collecting mcp==1.6.0
#10 96.30   Downloading mcp-1.6.0-py3-none-any.whl (76 kB)
#10 96.40      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 76.1/76.1 kB 674.9 kB/s eta 0:00:00
#10 97.65 Collecting numpy==2.2.5
#10 97.72   Downloading numpy-2.2.5-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (14.4 MB)
#10 116.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 14.4/14.4 MB 854.3 kB/s eta 0:00:00
#10 116.8 Collecting openai==1.76.0
#10 116.9   Downloading openai-1.76.0-py3-none-any.whl (661 kB)
#10 117.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 661.2/661.2 kB 1.1 MB/s eta 0:00:00
#10 117.7 Collecting opentelemetry-api==1.32.1
#10 117.8   Downloading opentelemetry_api-1.32.1-py3-none-any.whl (65 kB)
#10 117.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 65.3/65.3 kB 1.4 MB/s eta 0:00:00
#10 117.9 Collecting opentelemetry-exporter-gcp-trace==1.9.0
#10 118.0   Downloading opentelemetry_exporter_gcp_trace-1.9.0-py3-none-any.whl (13 kB)
#10 118.1 Collecting opentelemetry-resourcedetector-gcp==1.9.0a0
#10 118.1   Downloading opentelemetry_resourcedetector_gcp-1.9.0a0-py3-none-any.whl (20 kB)
#10 118.3 Collecting opentelemetry-sdk==1.32.1
#10 118.4   Downloading opentelemetry_sdk-1.32.1-py3-none-any.whl (118 kB)
#10 118.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 119.0/119.0 kB 1.2 MB/s eta 0:00:00
#10 118.6 Collecting opentelemetry-semantic-conventions==0.53b1
#10 118.7   Downloading opentelemetry_semantic_conventions-0.53b1-py3-none-any.whl (188 kB)
#10 118.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 188.4/188.4 kB 1.3 MB/s eta 0:00:00
#10 119.0 Collecting packaging==25.0
#10 119.0   Downloading packaging-25.0-py3-none-any.whl (66 kB)
#10 119.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66.5/66.5 kB 1.8 MB/s eta 0:00:00
#10 119.2 Collecting passlib[bcrypt]==1.7.4
#10 119.2   Downloading passlib-1.7.4-py2.py3-none-any.whl (525 kB)
#10 119.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 525.6/525.6 kB 1.4 MB/s eta 0:00:00
#10 121.3 Collecting pillow==11.2.1
#10 121.3   Downloading pillow-11.2.1-cp310-cp310-manylinux_2_28_aarch64.whl (4.5 MB)
#10 126.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 4.5/4.5 MB 940.4 kB/s eta 0:00:00
#10 126.2 Collecting pluggy==1.5.0
#10 126.3   Downloading pluggy-1.5.0-py3-none-any.whl (20 kB)
#10 126.5 Collecting proto-plus==1.26.1
#10 126.6   Downloading proto_plus-1.26.1-py3-none-any.whl (50 kB)
#10 126.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 50.2/50.2 kB 1.0 MB/s eta 0:00:00
#10 127.7 Collecting protobuf<6.0.0,>=3.20.2
#10 127.8   Downloading protobuf-5.29.5-cp38-abi3-manylinux2014_aarch64.whl (319 kB)
#10 128.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 319.8/319.8 kB 928.7 kB/s eta 0:00:00
#10 128.3 Collecting pyasn1==0.6.1
#10 128.4   Downloading pyasn1-0.6.1-py3-none-any.whl (83 kB)
#10 128.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.1/83.1 kB 1.2 MB/s eta 0:00:00
#10 128.6 Collecting pyasn1_modules==0.4.2
#10 128.7   Downloading pyasn1_modules-0.4.2-py3-none-any.whl (181 kB)
#10 128.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 181.3/181.3 kB 1.1 MB/s eta 0:00:00
#10 129.0 Collecting pycparser==2.22
#10 129.0   Downloading pycparser-2.22-py3-none-any.whl (117 kB)
#10 129.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 117.6/117.6 kB 1.3 MB/s eta 0:00:00
#10 130.2 Collecting pydantic==2.11.3
#10 130.2   Downloading pydantic-2.11.3-py3-none-any.whl (443 kB)
#10 130.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 443.6/443.6 kB 1.0 MB/s eta 0:00:00
#10 130.8 Collecting pydantic-settings==2.9.1
#10 130.8   Downloading pydantic_settings-2.9.1-py3-none-any.whl (44 kB)
#10 130.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 44.4/44.4 kB 1.9 MB/s eta 0:00:00
#10 134.3 Collecting pydantic_core==2.33.1
#10 134.4   Downloading pydantic_core-2.33.1-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
#10 135.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.9/1.9 MB 1.3 MB/s eta 0:00:00
#10 136.0 Collecting pyparsing==3.2.3
#10 136.1   Downloading pyparsing-3.2.3-py3-none-any.whl (111 kB)
#10 136.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 111.1/111.1 kB 1.4 MB/s eta 0:00:00
#10 136.3 Collecting pytest==8.3.5
#10 136.4   Downloading pytest-8.3.5-py3-none-any.whl (343 kB)
#10 136.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 343.6/343.6 kB 1.3 MB/s eta 0:00:00
#10 136.8 Collecting python-jose[cryptography]==3.3.0
#10 136.8   Downloading python_jose-3.3.0-py2.py3-none-any.whl (33 kB)
#10 136.9 Collecting python-multipart==0.0.9
#10 137.0   Downloading python_multipart-0.0.9-py3-none-any.whl (22 kB)
#10 137.1 Collecting qdrant-client==1.12.1
#10 137.2   Downloading qdrant_client-1.12.1-py3-none-any.whl (267 kB)
#10 137.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 267.2/267.2 kB 1.7 MB/s eta 0:00:00
#10 137.5 Collecting pytest-asyncio==0.26.0
#10 137.5   Downloading pytest_asyncio-0.26.0-py3-none-any.whl (19 kB)
#10 137.6 Collecting python-dateutil==2.9.0.post0
#10 137.7   Downloading python_dateutil-2.9.0.post0-py2.py3-none-any.whl (229 kB)
#10 137.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 229.9/229.9 kB 1.2 MB/s eta 0:00:00
#10 138.5 Collecting python-dotenv==1.1.0
#10 138.5   Downloading python_dotenv-1.1.0-py3-none-any.whl (20 kB)
#10 138.8 Collecting PyYAML==6.0.2
#10 138.9   Downloading PyYAML-6.0.2-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (718 kB)
#10 139.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 718.5/718.5 kB 1.2 MB/s eta 0:00:00
#10 139.7 Collecting requests==2.32.3
#10 139.7   Downloading requests-2.32.3-py3-none-any.whl (64 kB)
#10 139.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 64.9/64.9 kB 2.0 MB/s eta 0:00:00
#10 139.8 Collecting retry>=0.9.2
#10 139.9   Downloading retry-0.9.2-py2.py3-none-any.whl (8.0 kB)
#10 140.0 Collecting rsa==4.9.1
#10 140.0   Downloading rsa-4.9.1-py3-none-any.whl (34 kB)
#10 141.2 Collecting scikit-learn==1.6.1
#10 141.3   Downloading scikit_learn-1.6.1-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (12.6 MB)
#10 158.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12.6/12.6 MB 676.3 kB/s eta 0:00:00
#10 160.0 Collecting scipy==1.15.2
#10 160.0   Downloading scipy-1.15.2-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (35.5 MB)
#10 186.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 35.5/35.5 MB 1.3 MB/s eta 0:00:00
#10 187.6 Collecting shapely==2.1.0
#10 187.6   Downloading shapely-2.1.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (2.9 MB)
#10 189.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.9/2.9 MB 1.4 MB/s eta 0:00:00
#10 189.9 Collecting six==1.17.0
#10 189.9   Downloading six-1.17.0-py2.py3-none-any.whl (11 kB)
#10 190.0 Collecting slowapi==0.1.9
#10 190.1   Downloading slowapi-0.1.9-py3-none-any.whl (14 kB)
#10 190.2 Collecting sniffio==1.3.1
#10 190.2   Downloading sniffio-1.3.1-py3-none-any.whl (10 kB)
#10 191.9 Collecting SQLAlchemy==2.0.40
#10 192.0   Downloading sqlalchemy-2.0.40-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (3.1 MB)
#10 194.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.1/3.1 MB 1.4 MB/s eta 0:00:00
#10 194.3 Collecting sse-starlette==2.3.3
#10 194.3   Downloading sse_starlette-2.3.3-py3-none-any.whl (10 kB)
#10 194.4 Collecting starlette==0.46.2
#10 194.5   Downloading starlette-0.46.2-py3-none-any.whl (72 kB)
#10 194.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 72.0/72.0 kB 2.0 MB/s eta 0:00:00
#10 194.6 Collecting threadpoolctl==3.6.0
#10 194.7   Downloading threadpoolctl-3.6.0-py3-none-any.whl (18 kB)
#10 194.8 Collecting tomli==2.2.1
#10 194.9   Downloading tomli-2.2.1-py3-none-any.whl (14 kB)
#10 195.1 Collecting tqdm==4.67.1
#10 195.1   Downloading tqdm-4.67.1-py3-none-any.whl (78 kB)
#10 195.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 78.5/78.5 kB 1.6 MB/s eta 0:00:00
#10 195.3 Collecting typing-inspection==0.4.0
#10 195.3   Downloading typing_inspection-0.4.0-py3-none-any.whl (14 kB)
#10 195.5 Collecting typing_extensions==4.13.2
#10 195.5   Downloading typing_extensions-4.13.2-py3-none-any.whl (45 kB)
#10 195.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45.8/45.8 kB 2.1 MB/s eta 0:00:00
#10 195.6 Collecting tzlocal==5.3.1
#10 195.7   Downloading tzlocal-5.3.1-py3-none-any.whl (18 kB)
#10 195.8 Collecting uritemplate==4.1.1
#10 195.9   Downloading uritemplate-4.1.1-py2.py3-none-any.whl (10 kB)
#10 196.0 Collecting urllib3==2.4.0
#10 196.1   Downloading urllib3-2.4.0-py3-none-any.whl (128 kB)
#10 196.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 128.7/128.7 kB 1.8 MB/s eta 0:00:00
#10 196.3 Collecting uvicorn==0.34.2
#10 196.4   Downloading uvicorn-0.34.2-py3-none-any.whl (62 kB)
#10 196.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 62.5/62.5 kB 2.2 MB/s eta 0:00:00
#10 196.6 Collecting uvloop==0.21.0
#10 196.7   Downloading uvloop-0.21.0-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (3.8 MB)
#10 202.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.8/3.8 MB 704.1 kB/s eta 0:00:00
#10 202.5 Collecting watchfiles==1.0.5
#10 202.6   Downloading watchfiles-1.0.5-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (455 kB)
#10 203.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 455.0/455.0 kB 740.2 kB/s eta 0:00:00
#10 203.7 Collecting websockets==15.0.1
#10 203.8   Downloading websockets-15.0.1-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (182 kB)
#10 204.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 182.3/182.3 kB 1.0 MB/s eta 0:00:00
#10 204.1 Collecting Werkzeug<3.0,>=2.3
#10 204.1   Downloading werkzeug-2.3.8-py3-none-any.whl (242 kB)
#10 204.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 242.3/242.3 kB 883.2 kB/s eta 0:00:00
#10 204.8 Collecting wrapt==1.17.2
#10 204.9   Downloading wrapt-1.17.2-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (83 kB)
#10 204.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 83.3/83.3 kB 1.2 MB/s eta 0:00:00
#10 205.0 Collecting zipp==3.21.0
#10 205.1   Downloading zipp-3.21.0-py3-none-any.whl (9.6 kB)
#10 205.4 Collecting google-cloud-logging>=3.9.0
#10 205.5   Downloading google_cloud_logging-3.12.1-py2.py3-none-any.whl (229 kB)
#10 205.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 229.5/229.5 kB 1.1 MB/s eta 0:00:00
#10 206.5 Collecting google-cloud-billing>=1.12.0
#10 206.6   Downloading google_cloud_billing-1.16.3-py3-none-any.whl (115 kB)
#10 206.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 115.8/115.8 kB 1.0 MB/s eta 0:00:00
#10 206.8 Collecting google-cloud-run>=0.10.18
#10 206.9   Downloading google_cloud_run-0.10.18-py3-none-any.whl (333 kB)
#10 207.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 333.8/333.8 kB 1.1 MB/s eta 0:00:00
#10 207.5 Collecting google-cloud-billing-budgets>=1.10.0
#10 207.6   Downloading google_cloud_billing_budgets-1.17.2-py3-none-any.whl (107 kB)
#10 207.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 107.9/107.9 kB 1.4 MB/s eta 0:00:00
#10 208.0 Collecting psutil>=5.9.0
#10 208.0   Downloading psutil-7.0.0-cp36-abi3-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (279 kB)
#10 208.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 279.5/279.5 kB 1.2 MB/s eta 0:00:00
#10 208.4 Collecting google-cloud-monitoring>=2.0.0
#10 208.5   Downloading google_cloud_monitoring-2.27.2-py3-none-any.whl (383 kB)
#10 208.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 383.7/383.7 kB 924.5 kB/s eta 0:00:00
#10 209.5 Collecting google-api-core[grpc]!=2.0.*,!=2.1.*,!=2.2.*,!=2.3.*,!=2.4.*,!=2.5.*,!=2.6.*,!=2.7.*,<3.0.0,>=1.34.1
#10 209.5   Downloading google_api_core-2.25.1-py3-none-any.whl (160 kB)
#10 209.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 160.8/160.8 kB 798.6 kB/s eta 0:00:00
#10 210.5 Collecting bcrypt>=3.1.0
#10 210.6   Downloading bcrypt-4.3.0-cp39-abi3-manylinux_2_34_aarch64.whl (279 kB)
#10 210.9      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 279.2/279.2 kB 1.1 MB/s eta 0:00:00
#10 211.2 Collecting ecdsa!=0.15
#10 211.3   Downloading ecdsa-0.19.1-py2.py3-none-any.whl (150 kB)
#10 211.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 150.6/150.6 kB 641.0 kB/s eta 0:00:00
#10 213.5 Collecting grpcio-tools>=1.41.0
#10 213.6   Downloading grpcio_tools-1.73.1-cp310-cp310-manylinux_2_17_aarch64.whl (2.5 MB)
#10 216.7      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.5/2.5 MB 806.2 kB/s eta 0:00:00
#10 216.8 Collecting portalocker<3.0.0,>=2.7.0
#10 216.8   Downloading portalocker-2.10.1-py3-none-any.whl (18 kB)
#10 217.2 Collecting limits>=2.3
#10 217.3   Downloading limits-5.4.0-py3-none-any.whl (60 kB)
#10 217.3      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 61.0/61.0 kB 1.0 MB/s eta 0:00:00
#10 217.9 Collecting greenlet>=1
#10 218.0   Downloading greenlet-3.2.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl (627 kB)
#10 218.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 627.4/627.4 kB 966.9 kB/s eta 0:00:00
#10 218.9 Collecting itsdangerous>=2.1.2
#10 219.0   Downloading itsdangerous-2.2.0-py3-none-any.whl (16 kB)
#10 219.1 Collecting blinker>=1.6.2
#10 219.1   Downloading blinker-1.9.0-py3-none-any.whl (8.5 kB)
#10 219.2 Collecting Jinja2>=3.1.2
#10 219.3   Downloading jinja2-3.1.6-py3-none-any.whl (134 kB)
#10 219.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 134.9/134.9 kB 1.1 MB/s eta 0:00:00
#10 219.6 Collecting py<2.0.0,>=1.4.26
#10 219.7   Downloading py-1.11.0-py2.py3-none-any.whl (98 kB)
#10 219.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 98.7/98.7 kB 1.3 MB/s eta 0:00:00
#10 219.8 Collecting decorator>=3.4.2
#10 219.9   Downloading decorator-5.2.1-py3-none-any.whl (9.2 kB)
#10 220.2 Collecting MarkupSafe>=2.1.1
#10 220.2   Downloading MarkupSafe-3.0.2-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (21 kB)
#10 220.3 Collecting google-cloud-appengine-logging<2.0.0,>=0.1.3
#10 220.4   Downloading google_cloud_appengine_logging-1.6.2-py3-none-any.whl (16 kB)
#10 220.5 Collecting google-cloud-audit-log<1.0.0,>=0.3.1
#10 220.5   Downloading google_cloud_audit_log-0.3.2-py3-none-any.whl (32 kB)
#10 220.8 Collecting google-api-core[grpc]!=2.0.*,!=2.1.*,!=2.2.*,!=2.3.*,!=2.4.*,!=2.5.*,!=2.6.*,!=2.7.*,<3.0.0,>=1.34.1
#10 220.8   Downloading google_api_core-2.25.0-py3-none-any.whl (160 kB)
#10 221.0      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 160.7/160.7 kB 1.3 MB/s eta 0:00:00
#10 221.1 Requirement already satisfied: setuptools in /usr/local/lib/python3.10/site-packages (from grpcio-tools>=1.41.0->qdrant-client==1.12.1->-r requirements.txt (line 80)) (65.5.1)
#10 221.1 Collecting grpcio-tools>=1.41.0
#10 221.2   Downloading grpcio_tools-1.73.0-cp310-cp310-manylinux_2_17_aarch64.whl (2.5 MB)
#10 224.6      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.5/2.5 MB 741.7 kB/s eta 0:00:00
#10 224.7   Downloading grpcio_tools-1.72.2-cp310-cp310-manylinux_2_17_aarch64.whl (2.4 MB)
#10 227.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.4/2.4 MB 828.4 kB/s eta 0:00:00
#10 227.6   Downloading grpcio_tools-1.72.1-cp310-cp310-manylinux_2_17_aarch64.whl (2.4 MB)
#10 230.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.4/2.4 MB 919.5 kB/s eta 0:00:00
#10 230.3   Downloading grpcio_tools-1.71.2-cp310-cp310-manylinux_2_17_aarch64.whl (2.3 MB)
#10 232.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.3/2.3 MB 1.3 MB/s eta 0:00:00
#10 232.5   Downloading grpcio_tools-1.71.0-cp310-cp310-manylinux_2_17_aarch64.whl (2.4 MB)
#10 234.2      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.4/2.4 MB 1.4 MB/s eta 0:00:00
#10 234.6   Downloading grpcio_tools-1.70.0-cp310-cp310-manylinux_2_17_aarch64.whl (2.3 MB)
#10 237.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.3/2.3 MB 781.8 kB/s eta 0:00:00
#10 237.6   Downloading grpcio_tools-1.69.0-cp310-cp310-manylinux_2_17_aarch64.whl (2.4 MB)
#10 241.8      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.4/2.4 MB 569.8 kB/s eta 0:00:00
#10 242.1   Downloading grpcio_tools-1.68.1-cp310-cp310-manylinux_2_17_aarch64.whl (2.3 MB)
#10 245.5      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.3/2.3 MB 693.1 kB/s eta 0:00:00
#10 245.5   Downloading grpcio_tools-1.68.0-cp310-cp310-manylinux_2_17_aarch64.whl (2.3 MB)
#10 248.1      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.3/2.3 MB 913.6 kB/s eta 0:00:00
#10 248.2 Collecting h2<5,>=3
#10 248.3   Downloading h2-4.2.0-py3-none-any.whl (60 kB)
#10 248.4      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 61.0/61.0 kB 1.1 MB/s eta 0:00:00
#10 248.6 Collecting hpack<5,>=4.1
#10 248.6   Downloading hpack-4.1.0-py3-none-any.whl (34 kB)
#10 248.7 Collecting hyperframe<7,>=6.1
#10 248.8   Downloading hyperframe-6.1.0-py3-none-any.whl (13 kB)
#10 249.7 Installing collected packages: passlib, zipp, wrapt, websockets, uvloop, urllib3, uritemplate, tzlocal, typing_extensions, tqdm, tomli, threadpoolctl, sniffio, six, PyYAML, python-multipart, python-dotenv, pyparsing, pycparser, pyasn1, py, psutil, protobuf, portalocker, pluggy, pillow, packaging, numpy, MarkupSafe, kiwisolver, joblib, jiter, itsdangerous, iniconfig, idna, hyperframe, httpx-sse, httptools, hpack, h11, grpcio, greenlet, graphviz, google-crc32c, fonttools, exceptiongroup, docstring_parser, distro, decorator, cycler, click, charset-normalizer, certifi, cachetools, blinker, bcrypt, annotated-types, Werkzeug, uvicorn, typing-inspection, SQLAlchemy, shapely, scipy, rsa, retry, requests, python-dateutil, pytest, pydantic_core, pyasn1_modules, proto-plus, Jinja2, importlib_metadata, httplib2, httpcore, h2, grpcio-tools, googleapis-common-protos, google-resumable-media, faiss-cpu, ecdsa, Deprecated, contourpy, cffi, anyio, watchfiles, starlette, scikit-learn, python-jose, pytest-asyncio, pydantic, opentelemetry-api, matplotlib, limits, httpx, grpcio-status, google-cloud-audit-log, google-auth, freezegun, Flask, cryptography, sse-starlette, slowapi, pydantic-settings, opentelemetry-semantic-conventions, openai, grpc-google-iam-v1, google-genai, google-auth-httplib2, google-api-core, fastapi, Authlib, qdrant-client, opentelemetry-sdk, mcp, google-cloud-core, google-api-python-client, opentelemetry-resourcedetector-gcp, google-cloud-trace, google-cloud-storage, google-cloud-speech, google-cloud-secret-manager, google-cloud-run, google-cloud-resource-manager, google-cloud-monitoring, google-cloud-firestore, google-cloud-billing-budgets, google-cloud-billing, google-cloud-bigquery, google-cloud-appengine-logging, opentelemetry-exporter-gcp-trace, google-cloud-logging, google-cloud-aiplatform, google-adk
#10 266.1 Successfully installed Authlib-1.5.2 Deprecated-1.2.18 Flask-2.3.3 Jinja2-3.1.6 MarkupSafe-3.0.2 PyYAML-6.0.2 SQLAlchemy-2.0.40 Werkzeug-2.3.8 annotated-types-0.7.0 anyio-4.9.0 bcrypt-4.3.0 blinker-1.9.0 cachetools-5.5.2 certifi-2025.4.26 cffi-1.17.1 charset-normalizer-3.4.1 click-8.1.8 contourpy-1.3.2 cryptography-44.0.2 cycler-0.12.1 decorator-5.2.1 distro-1.9.0 docstring_parser-0.16 ecdsa-0.19.1 exceptiongroup-1.2.2 faiss-cpu-1.11.0 fastapi-0.115.12 fonttools-4.57.0 freezegun-1.5.1 google-adk-0.3.0 google-api-core-2.24.2 google-api-python-client-2.168.0 google-auth-2.39.0 google-auth-httplib2-0.2.0 google-cloud-aiplatform-1.90.0 google-cloud-appengine-logging-1.6.2 google-cloud-audit-log-0.3.2 google-cloud-bigquery-3.31.0 google-cloud-billing-1.16.3 google-cloud-billing-budgets-1.17.2 google-cloud-core-2.4.3 google-cloud-firestore-2.20.2 google-cloud-logging-3.12.1 google-cloud-monitoring-2.27.2 google-cloud-resource-manager-1.14.2 google-cloud-run-0.10.18 google-cloud-secret-manager-2.23.3 google-cloud-speech-2.32.0 google-cloud-storage-2.19.0 google-cloud-trace-1.16.1 google-crc32c-1.7.1 google-genai-1.12.1 google-resumable-media-2.7.2 googleapis-common-protos-1.70.0 graphviz-0.20.3 greenlet-3.2.3 grpc-google-iam-v1-0.14.2 grpcio-1.68.0 grpcio-status-1.68.0 grpcio-tools-1.68.0 h11-0.16.0 h2-4.2.0 hpack-4.1.0 httpcore-1.0.9 httplib2-0.22.0 httptools-0.6.4 httpx-0.28.1 httpx-sse-0.4.0 hyperframe-6.1.0 idna-3.10 importlib_metadata-8.6.1 iniconfig-2.1.0 itsdangerous-2.2.0 jiter-0.9.0 joblib-1.4.2 kiwisolver-1.4.8 limits-5.4.0 matplotlib-3.10.1 mcp-1.6.0 numpy-2.2.5 openai-1.76.0 opentelemetry-api-1.32.1 opentelemetry-exporter-gcp-trace-1.9.0 opentelemetry-resourcedetector-gcp-1.9.0a0 opentelemetry-sdk-1.32.1 opentelemetry-semantic-conventions-0.53b1 packaging-25.0 passlib-1.7.4 pillow-11.2.1 pluggy-1.5.0 portalocker-2.10.1 proto-plus-1.26.1 protobuf-5.29.5 psutil-7.0.0 py-1.11.0 pyasn1-0.6.1 pyasn1_modules-0.4.2 pycparser-2.22 pydantic-2.11.3 pydantic-settings-2.9.1 pydantic_core-2.33.1 pyparsing-3.2.3 pytest-8.3.5 pytest-asyncio-0.26.0 python-dateutil-2.9.0.post0 python-dotenv-1.1.0 python-jose-3.3.0 python-multipart-0.0.9 qdrant-client-1.12.1 requests-2.32.3 retry-0.9.2 rsa-4.9.1 scikit-learn-1.6.1 scipy-1.15.2 shapely-2.1.0 six-1.17.0 slowapi-0.1.9 sniffio-1.3.1 sse-starlette-2.3.3 starlette-0.46.2 threadpoolctl-3.6.0 tomli-2.2.1 tqdm-4.67.1 typing-inspection-0.4.0 typing_extensions-4.13.2 tzlocal-5.3.1 uritemplate-4.1.1 urllib3-2.4.0 uvicorn-0.34.2 uvloop-0.21.0 watchfiles-1.0.5 websockets-15.0.1 wrapt-1.17.2 zipp-3.21.0
#10 266.1 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv
#10 266.5 
#10 266.5 [notice] A new release of pip is available: 23.0.1 -> 25.1.1
#10 266.5 [notice] To update, run: pip install --upgrade pip
#10 DONE 267.7s

#11 [ 6/21] COPY pytest.ini .
#11 DONE 0.1s

#12 [ 7/21] COPY conftest.py .
#12 DONE 0.0s

#13 [ 8/21] COPY __init__.py .
#13 DONE 0.0s

#14 [ 9/21] COPY src/ ./src/
#14 DONE 0.7s

#15 [10/21] COPY tests/ ./tests/
#15 DONE 0.0s

#16 [11/21] COPY tools/ ./tools/
#16 DONE 0.0s

#17 [12/21] COPY mcp/ ./mcp/
#17 DONE 0.0s

#18 [13/21] COPY agent/ ./agent/
#18 DONE 0.0s

#19 [14/21] COPY auth/ ./auth/
#19 DONE 0.0s

#20 [15/21] COPY config/ ./config/
#20 DONE 0.0s

#21 [16/21] COPY api/ ./api/
#21 DONE 0.0s

#22 [17/21] COPY vector_store/ ./vector_store/
#22 DONE 0.0s

#23 [18/21] COPY utils/ ./utils/
#23 DONE 0.0s

#24 [19/21] COPY ADK/ ./ADK/
#24 DONE 0.0s

#25 [20/21] COPY api_mcp_gateway.py .
#25 DONE 0.0s

#26 [21/21] COPY *.py .
#26 DONE 0.0s

#27 exporting to image
#27 exporting layers
#27 exporting layers 16.9s done
#27 exporting manifest sha256:e7202dacffecb5e31309238778f2fdb4d01387bfd640ccb4be30cdc6af0c692d done
#27 exporting config sha256:156a5cbbde126e211507f47bad31b2e974435d3db9b1ec2ca8d9b9ef0988bd84 done
#27 exporting attestation manifest sha256:95f21f69cca4a9bd2df64d7f418e672d801996ddeefc08942c6b926bf32a2bf7 done
#27 exporting manifest list sha256:535b45c843777b9f18bae96ef5cf11405cc3ff6aa7bd108c763c0049c7a8e74e done
#27 naming to docker.io/library/test-build:local done
#27 unpacking to docker.io/library/test-build:local
#27 unpacking to docker.io/library/test-build:local 6.8s done
#27 DONE 23.7s

View build details: docker-desktop://dashboard/build/desktop-linux/desktop-linux/qlamwxenpt490iq0de7obyxk9
============================= test session starts ==============================
platform linux -- Python 3.10.17, pytest-8.3.5, pluggy-1.5.0
rootdir: /app
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.9.0, asyncio-0.26.0
asyncio: mode=auto, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
>>> Collected 506 tests (manifest filtering disabled)
collected 506 items / 504 deselected / 2 selected

tests/test_meta_counts.py ..                                             [100%]

====================== 2 passed, 504 deselected in 2.34s =======================

## .env.sample
- Result: Updated with required variables

## Test Logic
- Result: pytest.ini:markers =

## CI Stability
- Result: [{"conclusion":""}]

## Backup
- Result: total 120
drwx------@ 65535 nmhuyen  staff    64 Jun 29 17:36 agent_data_backup_2025-06-29_17-33-11
drwxr-xr-x@    10 nmhuyen  staff   320 Jun 28 18:00 Docker_push_r1.26
drwxr-xr-x@    27 nmhuyen  staff   864 Jun 28 16:09 Docker_rebuild_backup_r1.25B
drwxr-xr-x@     7 nmhuyen  staff   224 Jun 28 16:22 Docker_rebuild_backup_r1.25C
-rw-r--r--@     1 nmhuyen  staff  1487 Jun 29 16:51 docker_system_metadata.json
-rw-r--r--@     1 nmhuyen  staff  1214 Jun 28 09:53 Dockerfile
-rw-------@     1 nmhuyen  staff  1258 Jun 28 13:33 Dockerfile_r1.24_20250628_1340.backup
-rw-r--r--@     1 nmhuyen  staff  1214 Jun 28 14:07 Dockerfile.20250628_140707
-rw-r--r--@     1 nmhuyen  staff  1214 Jun 28 15:29 Dockerfile.20250628_152911
-rw-r--r--@     1 nmhuyen  staff  1214 Jun 28 15:40 Dockerfile.20250628_154004
drwxr-xr-x@    13 nmhuyen  staff   416 Jun 29 11:17 r1.29A_docker_cleanup
drwxr-xr-x@     2 nmhuyen  staff    64 Jun 29 11:25 r1.29A.1_docker_cleanup_20250629_112554
drwxr-xr-x@     2 nmhuyen  staff    64 Jun 29 11:26 r1.29A.1_docker_cleanup_20250629_112608
drwxr-xr-x@     6 nmhuyen  staff   192 Jun 29 11:26 r1.29A.1_docker_cleanup_20250629_112620
drwxr-xr-x@     4 nmhuyen  staff   128 Jun 29 11:26 r1.29A.1_docker_cleanup_20250629_112623
drwxr-xr-x@     3 nmhuyen  staff    96 Jun 29 11:26 r1.29A.1_docker_cleanup_20250629_112625
drwxr-xr-x@     3 nmhuyen  staff    96 Jun 29 11:26 r1.29A.1_docker_cleanup_20250629_112636
-rw-r--r--@     1 nmhuyen  staff  1042 Jun 29 16:46 r1.29C_cleanup_summary.md
-rw-r--r--@     1 nmhuyen  staff  4607 Jun 29 16:46 r1.29C_docker_cleanup_report.md
-rw-r--r--@     1 nmhuyen  staff   832 Jun 29 16:51 r1.29D_docker_metadata_backup.json
-rw-r--r--@     1 nmhuyen  staff  3424 Jun 29 16:58 r1.29D_final_cleanup_summary.md
-rw-r--r--@     1 nmhuyen  staff  2610 Jun 29 16:57 r1.29D_github_registry_cleanup_instructions.md
-rw-r--r--@     1 nmhuyen  staff  1840 Jun 29 16:58 r1.29D_maintenance_commands.md
-rw-r--r--@     1 nmhuyen  staff  2291 Jun 27 09:47 README.md
-rw-------@     1 nmhuyen  staff  2421 Jun 27 09:47 requirements_r1.24_20250628_1340.backup
-rw-r--r--@     1 nmhuyen  staff  2421 Jun 28 14:07 requirements.20250628_140707.txt
-rw-r--r--@     1 nmhuyen  staff  2421 Jun 28 09:53 requirements.txt
-rw-r--r--@     1 nmhuyen  staff     0 Jun 27 08:36 test_write_from_terminal.txt
drwx------@ 65535 nmhuyen  staff    64 Jun 28 10:15 venv_clean_backup_20250628_101542

## Conclusion
- Repo complete: [Pending verification]
- Stable: [Pending CI and test results]
