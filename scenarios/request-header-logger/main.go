package main

import (
	"log"
	"net/http"
)

// LogAllHeaders logs all headers of the incoming request.
func LogAllHeaders(w http.ResponseWriter, r *http.Request) {
	// Log all headers
	log.Println("Request Headers:")
	for name, values := range r.Header {
		for _, value := range values {
			log.Printf("%s: %s", name, value)
		}
	}

	// Respond with a simple message
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("Headers logged successfully"))
}

func main() {
	// Set up a simple HTTP server to listen on port 8080
	http.HandleFunc("/", LogAllHeaders)
	log.Println("Server starting on port 8080...")
	err := http.ListenAndServe(":8080", nil)
	if err != nil {
		log.Fatalf("Error starting server: %v", err)
	}
}

