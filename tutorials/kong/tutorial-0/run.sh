helm repo add kong https://charts.konghq.com
helm repo update
helm install kong kong/kong -n kong --create-namespace --set proxy.type=NodePort