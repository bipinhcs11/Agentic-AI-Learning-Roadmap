package com.example.aiidentity.agent;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AgentRepository extends JpaRepository<AgentRegistration, UUID> {}
