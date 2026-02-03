FROM hub.hamdocker.ir/golang:1.25-alpine as builder

WORKDIR /app

COPY main.go .

RUN go build -o header-logger main.go

FROM hub.hamdocker.ir/alpine:latest

WORKDIR /app

COPY --from=builder /app/header-logger .

CMD ["./header-logger"]

