
#!/usr/bin/env sh
export CA_BUNDLE="$(cat ca.crt | base64 -w0)"
envsubst
