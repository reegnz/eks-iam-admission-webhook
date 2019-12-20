# EKS IAM Role identity webhook

This is a proof of concept reimplementing
https://github.com/aws/amazon-eks-pod-identity-webhook/ in python.

I wanted to learn how to write an  admission controller in a language other
than go. ;)

## Installation

Generate certificate for the admission controller:

```
./create-certificate.sh eks-iam-admission-controller default
```

Register webhook with generated certificate:

```
cat webhook-config.yaml | ./template-cert.sh | kubectl apply -f -
```

Deploy webhook:

```
skaffold run
```
