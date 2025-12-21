FROM golang:1.25-alpine as builder

WORKDIR /app

COPY main.go .

RUN go build -o header-logger main.go

FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/header-logger .

CMD ["./header-logger"]

