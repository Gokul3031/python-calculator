# Python Calculator --- Kubernetes, GitOps & Monitoring

A Flask-based calculator deployed to Kubernetes with Docker, GitHub
Actions, GitHub Container Registry (GHCR), Argo CD, Prometheus, and
Grafana.

> **Project status:** This README documents the current lab setup and
> the intended CI/CD workflow. Confirm the live workflow and cluster
> configuration before describing every step as fully automated.

## Table of Contents

-   [Overview](#overview)
-   [Architecture](#architecture)
-   [Features](#features)
-   [Technology Stack](#technology-stack)
-   [Repository Structure](#repository-structure)
-   [Application](#application)
-   [Run Locally](#run-locally)
-   [Build and Run with Docker](#build-and-run-with-docker)
-   [Kubernetes Deployment](#kubernetes-deployment)
-   [CI/CD and GitOps](#cicd-and-gitops)
-   [Prometheus Monitoring](#prometheus-monitoring)
-   [Grafana Dashboards](#grafana-dashboards)
-   [TPS and Load Testing](#tps-and-load-testing)
-   [Screenshots](#screenshots)
-   [Troubleshooting](#troubleshooting)
-   [Future Improvements](#future-improvements)

## Overview

This project demonstrates how to take a small Python web application and
operate it using common DevOps practices:

1.  Develop a Flask calculator with an HTML interface.
2.  Package the application in a Docker image.
3.  Build and publish images to GHCR with GitHub Actions.
4.  Deploy the application to Kubernetes.
5.  Use Argo CD to reconcile Kubernetes manifests from Git.
6.  Scrape application metrics with Prometheus and visualize them in
    Grafana.
7.  Run controlled load tests and observe throughput, latency, errors,
    and pod resource usage.

## Architecture

``` mermaid
flowchart TD
    Dev[Developer pushes code] --> GH[GitHub repository]
    GH --> Actions[GitHub Actions CI]
    Actions --> Image[Build Docker image]
    Image --> GHCR[GitHub Container Registry]
    Actions --> Manifest[Update image tag in Kubernetes manifest]
    Manifest --> GH
    GH --> Argo[Argo CD watches Git]
    Argo --> K8s[Kubernetes cluster]
    K8s --> SVC[python-calculator Service]
    SVC --> P1[Calculator Pod 1]
    SVC --> P2[Calculator Pod 2]
    SVC --> P3[Calculator Pod 3]
    SVC --> P4[Calculator Pod 4]
    SVC --> P5[Calculator Pod 5]
    P1 --> Metrics[/metrics endpoint/]
    P2 --> Metrics
    P3 --> Metrics
    P4 --> Metrics
    P5 --> Metrics
    Metrics --> Prom[Prometheus]
    Prom --> Grafana[Grafana dashboards]
```

The diagram represents the intended end-to-end flow. The CI
manifest-update step and GHCR cleanup step depend on the repository's
current workflow configuration and secrets.

## Features

-   Flask calculator supporting addition, subtraction, multiplication,
    and division.
-   Input validation and division-by-zero handling.
-   Light and dark theme toggle in the web interface, with the selected
    theme stored in browser local storage.
-   Dockerized application served by Gunicorn.
-   Kubernetes Deployment with multiple replicas.
-   Kubernetes Service of type `LoadBalancer`.
-   GitHub Actions workflow for image build and publication to GHCR.
-   Argo CD GitOps deployment from repository manifests.
-   Prometheus application metrics and Kubernetes resource monitoring.
-   Grafana dashboards for traffic, processing time, errors, CPU, and
    memory.
-   Mixed-transaction load testing with successful and intentionally
    invalid operations.

## Technology Stack

  -----------------------------------------------------------------------
  Area                                Technology
  ----------------------------------- -----------------------------------
  Application                         Python, Flask

  Web interface                       HTML, CSS, JavaScript

  Production server                   Gunicorn

  Containerization                    Docker

  Container registry                  GitHub Container Registry (GHCR)

  CI                                  GitHub Actions

  Deployment                          Kubernetes / Minikube

  GitOps                              Argo CD

  Metrics                             Prometheus,
                                      `prometheus-flask-exporter`,
                                      `prometheus_client`

  Dashboards                          Grafana

  Load testing                        Python standard library / optional
                                      `hey`
  -----------------------------------------------------------------------

## Repository Structure

The exact files may change as the project evolves. A typical layout is:

``` text
python-calculator/
├── app.py
├── monitor.py
├── requirements.txt
├── Dockerfile
├── templates/
│   └── index.html
├── k8s/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── servicemonitor.yaml
└── .github/
    └── workflows/
        └── ci-cd.yaml
```

-   `app.py`: Flask routes, calculator operations, and custom metrics.
-   `monitor.py`: application entry point used by Gunicorn; imports the
    Flask app and metrics.
-   `templates/index.html`: calculator UI and theme toggle.
-   `Dockerfile`: builds the application image.
-   `k8s/`: Kubernetes manifests managed through GitOps.
-   `.github/workflows/ci-cd.yaml`: CI workflow for building/publishing
    images and, if configured, updating deployment manifests.

## Application

The calculator supports:

-   Addition
-   Subtraction
-   Multiplication
-   Division
-   Division-by-zero error handling
-   Invalid input and unsupported-operation handling

The `/metrics` endpoint exposes Prometheus metrics. Custom metrics used
by the application include:

-   `calculator_operation_total`: calculator operations, labeled by
    operation and status.
-   `calculator_operation_duration_seconds`: histogram of
    application-side processing time.
-   `calculator_requests_total`: HTTP requests, labeled by method and
    application status.

The Flask Prometheus exporter may also expose standard request metrics.

> The custom `status` label represents the application's success/error
> result; it is not necessarily the HTTP response status code. Some
> handled application errors can return HTTP 200 while still
> incrementing the application error counter.

## Kubernetes Deployment

The application is deployed in the `calci` namespace. The Deployment has
been run with five replicas in the lab.

Inspect resources:

``` bash
kubectl get deployment -n calci
kubectl get pods -n calci -o wide
kubectl get svc python-calculator -n calci
kubectl get endpoints python-calculator -n calci
kubectl top pods -n calci
```

Inspect the configured container image:

``` bash
kubectl get deployment python-calculator -n calci \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
echo
```

### Service exposure

The Service is configured as `type: LoadBalancer` on port `5000`. In the
local Minikube lab, a NodePort such as `30080` has also been present.
The actual reachable address depends on the current Minikube networking
setup; a LoadBalancer Service may require `minikube tunnel`.

``` bash
kubectl get svc python-calculator -n calci
minikube ip
```

Do not assume a cluster-internal or virtual LoadBalancer IP is reachable
from the host until you verify it:

``` bash
curl -i --max-time 5 http://<reachable-address>:5000/
```

## CI/CD and GitOps

The GitHub Actions workflow has two jobs: `build` and `production`. The `production` job targets the GitHub Environment named `production`, where protection rules can require approval before deployment changes proceed.

### Pipeline stages

1. Push application code to the `main` branch. Changes limited to `k8s/**` are ignored by the workflow trigger.
2. **Build job:** checks out the repository, derives the image tag from `GITHUB_SHA`, logs in to GHCR, and builds/pushes both the immutable SHA-tagged image and the `latest` tag.
3. **Production approval:** the `production` job targets the GitHub Environment named `production`. If required reviewers are configured for that environment, GitHub pauses the job until approval is granted.
4. **Production job:** checks out `main`, updates `k8s/deployment.yaml` to use the SHA-tagged image, then commits and pushes the manifest change to `main`.
5. **Argo CD:** detects the manifest change and syncs the Kubernetes application, assuming it tracks the correct repository, branch, and `k8s/` path and automated sync is enabled.
6. **Kubernetes:** rolls out the new Deployment template using its configured update strategy.

The manifest commit is ignored by `paths-ignore: ["k8s/**"]`, which helps prevent a manifest-only commit from starting another image build.

### Configure production approval

In GitHub, open **Repository Settings → Environments → production**. Configure **Required reviewers**, add the intended reviewer(s), and save the protection rules. The workflow must reference the exact environment name:

```yaml
environment:
  name: production
```

In the supplied screenshot, `Gokul3031` is selected as a required reviewer. **Prevent self-review** is unchecked, so self-review is not explicitly prohibited by this setting. Enable it if you want a different person to approve production deployments. Environment protection availability can depend on repository visibility and GitHub plan.

### How the two jobs share the image tag

The `build` job exposes the image tag as a job output:

```yaml
outputs:
  image_tag: ${{ steps.set-tag.outputs.image_tag }}
```

The `production` job reads it using:

```yaml
env:
  IMAGE_TAG: ${{ needs.build.outputs.image_tag }}
```

Using the commit SHA makes the deployed image identifiable and avoids relying solely on the mutable `latest` tag.

### Verify CI/CD

- Check the `build` job for successful image publication.
- Confirm the workflow pauses at the `production` environment when approval is required.
- Approve the deployment in the GitHub Actions run.
- Check the `production` job for a successful manifest commit.
- Check Argo CD for `Synced` and `Healthy` status.
- Confirm the Deployment uses the new image SHA and the rollout completes.

```bash
kubectl get application python-calculator -n argocd
kubectl get pods -n calci
kubectl rollout status deployment/python-calculator -n calci
kubectl get deployment python-calculator -n calci \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
echo
```

## Prometheus Monitoring

The lab uses `kube-prometheus-stack` installed through Helm in the
`monitor` namespace. A `ServiceMonitor` in `calci` selects the
calculator Service and scrapes `/metrics`.

Useful checks:

``` bash
kubectl get pods -n monitor
kubectl get svc -n monitor
kubectl get servicemonitor -n calci
```

Prometheus should show the calculator target as `UP`. If it does not,
check the Service labels, `ServiceMonitor` selector/labels, endpoint
port name, and namespace selector.

### Application PromQL queries

**Successful calculator operations per second (success TPS):**

``` promql
sum(rate(calculator_operation_total{status="success"}[1m]))
```

**All recorded calculator operations per second:**

``` promql
sum(rate(calculator_operation_total[1m]))
```

**Application error rate (percentage):**

``` promql
100 *
(
  sum(rate(calculator_operation_total{status="error"}[5m])) or vector(0)
)
/
clamp_min(sum(rate(calculator_operation_total[5m])), 1e-9)
```

**Average application processing time (seconds):**

``` promql
sum(rate(calculator_operation_duration_seconds_sum[5m]))
/
clamp_min(sum(rate(calculator_operation_duration_seconds_count[5m])), 1e-9)
```

To display average processing time in milliseconds, multiply the result
by `1000`.

**P95 application processing time (seconds):**

``` promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(calculator_operation_duration_seconds_bucket[5m])
  )
)
```

**Total errors over the last five minutes:**

``` promql
sum(increase(calculator_operation_total{status="error"}[5m]))
```

These queries require the corresponding metric series to exist and be
scraped. Rate functions need enough samples in the selected time window.
If a label combination has never been observed, the series may not exist
yet.

### Kubernetes resource queries

**CPU usage by calculator pod (cores):**

``` promql
sum by (pod) (
  rate(container_cpu_usage_seconds_total{namespace="calci"}[5m])
)
```

**Memory working set by pod (bytes):**

``` promql
sum by (pod) (
  container_memory_working_set_bytes{namespace="calci"}
)
```

**Available Deployment replicas:**

``` promql
kube_deployment_status_replicas_available{
  namespace="calci",
  deployment="python-calculator"
}
```

**Ready calculator pods:**

``` promql
sum(
  kube_pod_status_ready{
    namespace="calci",
    pod=~"python-calculator-.*",
    condition="true"
  }
)
```

### Per-pod application traffic

The custom `calculator_operation_total` metric must contain a `pod`
label to attribute application operations directly to individual pods.
If it does not, grouping by `pod` will not work. Use Kubernetes resource
metrics for per-pod CPU/memory, or add pod identity to application
metrics through a deliberate instrumentation change.

To restrict a metric to pods that are currently Ready, join it with
`kube_pod_status_ready` only when both metric families share compatible
pod labels and the same namespace label conventions.

## Grafana Dashboards

Suggested dashboards:

1.  **Kubernetes Infrastructure Monitoring**
    -   Pod count and Ready replicas
    -   CPU usage by pod
    -   Memory usage by pod
    -   Deployment availability
2.  **Python Calculator --- Application Monitoring**
    -   Total operations
    -   Successful operations per second
    -   Average and p95 processing time
    -   Application error rate

For a rate query, set the unit to an appropriate operations-per-second
or requests-per-second unit. A `rate()` query shows a rate, not a
cumulative transaction count.

#