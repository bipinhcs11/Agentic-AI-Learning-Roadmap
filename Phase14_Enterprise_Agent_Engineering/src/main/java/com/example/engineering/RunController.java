package com.example.engineering;

import java.security.Principal;
import java.util.Map;
import java.util.UUID;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
class RunController {
    record CreateRun(@NotNull AgentLoop.Scenario scenario, @Min(1) @Max(8) int maxSteps) {}
    record Decision(@NotNull Boolean approved) {}
    private final RunService service;
    RunController(RunService service) { this.service = service; }

    @PostMapping("/runs")
    @ResponseStatus(HttpStatus.CREATED)
    RunService.Run create(@Valid @RequestBody CreateRun request, Principal principal) {
        return service.create(SecurityConfig.tenant(principal.getName()), request.scenario(), request.maxSteps());
    }

    @GetMapping("/runs/{id}")
    RunService.Run get(@PathVariable UUID id, Principal principal) {
        return service.get(id, SecurityConfig.tenant(principal.getName()));
    }

    @PostMapping("/runs/{id}/decision")
    RunService.Run decide(@PathVariable UUID id, @Valid @RequestBody Decision decision, Principal principal) {
        return service.decide(id, SecurityConfig.tenant(principal.getName()), principal.getName(), decision.approved());
    }

    @GetMapping("/catalog")
    Map<String, Object> catalog(Principal principal) {
        String tenant = SecurityConfig.tenant(principal.getName());
        return Map.of("tenant", tenant, "documentCount", service.catalogSize(tenant));
    }
}
