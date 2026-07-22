package com.example.aiidentity.api;

import static com.example.aiidentity.api.AgentApiModels.*;

import com.example.aiidentity.service.AgentIdentityService;
import jakarta.validation.Valid;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping
public class AgentController {
    private final AgentIdentityService service;

    public AgentController(AgentIdentityService service) {
        this.service = service;
    }

    @PostMapping("/agent/register")
    @ResponseStatus(HttpStatus.CREATED)
    AgentResponse register(@Valid @RequestBody RegisterAgentRequest request) {
        return service.register(request);
    }

    @GetMapping("/agent/{id}")
    AgentResponse get(@PathVariable UUID id) {
        return service.get(id);
    }

    @GetMapping("/agent/{id}/status")
    AgentStatusResponse status(@PathVariable UUID id) {
        return service.status(id);
    }

    @PostMapping("/agent/token")
    TokenResponse token(@Valid @RequestBody TokenRequest request) {
        return service.issueAgentToken(request);
    }

    @PostMapping("/agent/task-token")
    TokenResponse taskToken(@Valid @RequestBody TaskTokenRequest request) {
        return service.issueTaskToken(request);
    }

    @PostMapping("/agent/revoke")
    RevokeAgentResponse revoke(@Valid @RequestBody RevokeAgentRequest request) {
        return service.revoke(request);
    }

    @GetMapping("/task/{taskId}/status")
    TaskStatusResponse taskStatus(@PathVariable String taskId, @RequestParam UUID agentId) {
        return service.taskStatus(taskId, agentId);
    }

    @PostMapping("/task/revoke")
    RevokeTaskResponse revokeTask(@Valid @RequestBody RevokeTaskRequest request) {
        return service.revokeTask(request);
    }

    @GetMapping("/.well-known/jwks.json")
    Map<String, Object> jwks() {
        return service.publicJwks();
    }
}
