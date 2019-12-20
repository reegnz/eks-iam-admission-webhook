#!/usr/bin/env bash
set -euo pipefail

service=${1:-}
namespace=${2:-"default"}

cat <<EOF | yq '.' | cfssl genkey - | cfssljson -bare server
CN: ${service}.${namespace}.svc.cluster.local
hosts:
- ${service}.${namespace}.svc.cluster.local
- ${service}.${namespace}.svc
- ${service}.${namespace}
- ${service}
key:
  algo: ecdsa
  size: 256
EOF

# create namespace if not existing
if kubectl get ns ${namespace} 2>&1 >/dev/null; then
    echo 'namespace already exists' >&2 
else
    kubectl create ns ${namespace} --dry-run -o yaml | kubectl apply -f -
fi

# save CSR to configmap
kubectl create cm ${service}-csr \
    --from-file=server.csr \
    --dry-run -o yaml |\
    kubectl -n ${namespace} apply -f -


# create CSR in k8s API

cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1beta1
kind: CertificateSigningRequest
metadata:
  name: ${service}.${namespace}
spec:
  request: $(cat server.csr | base64 | tr -d '\n')
  usages:
  - digital signature
  - key encipherment
  - server auth
EOF
kubectl certificate approve ${service}.${namespace}

kubectl get csr ${service}.${namespace} -o jsonpath='{.status.certificate}' | base64 -d > server.crt

kubectl create secret tls ${service}-tls \
    --cert server.crt \
    --key server-key.pem \
    --dry-run -o yaml |\
    kubectl -n ${namespace} apply -f -


kubectl get secret -o jsonpath="{.items[?(@.type==\"kubernetes.io/service-account-token\")].data['ca\.crt']}" | base64 --decode > ca.crt
