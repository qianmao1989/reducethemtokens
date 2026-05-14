package main

import (
	"fmt"
	"strings"
)

type Config struct {
	Host string
	Port int
}

type Server struct {
	config Config
}

func NewServer(config Config) *Server {
	return &Server{config: config}
}

func (s *Server) Start() error {
	fmt.Printf("Starting on %s:%d\n", s.config.Host, s.config.Port)
	return nil
}

func (s *Server) Stop() {
	fmt.Println("Stopping")
}

func joinParts(parts []string, sep string) string {
	return strings.Join(parts, sep)
}
