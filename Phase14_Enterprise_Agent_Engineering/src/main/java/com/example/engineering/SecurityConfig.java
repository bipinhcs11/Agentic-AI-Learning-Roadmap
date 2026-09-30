package com.example.engineering;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
class SecurityConfig {
    @Bean
    UserDetailsService users() {
        // Public, fictional loopback-only credentials. Replace with enterprise OIDC.
        return new InMemoryUserDetailsManager(
            User.withUsername("reader").password("{noop}reader-demo").roles("READER").build(),
            User.withUsername("reviewer").password("{noop}reviewer-demo").roles("REVIEWER").build(),
            User.withUsername("other").password("{noop}other-demo").roles("READER").build());
    }

    @Bean
    SecurityFilterChain security(HttpSecurity http) throws Exception {
        return http
            // CLI-only local API: reject browser Origin requests and use no cookies/sessions.
            .csrf(csrf -> csrf.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(request -> request.getHeader("Origin") != null).denyAll()
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/runs/*/decision").hasRole("REVIEWER")
                .anyRequest().authenticated())
            .httpBasic(Customizer.withDefaults()).build();
    }

    static String tenant(String username) {
        return switch (username) {
            case "reader", "reviewer" -> "demo-a";
            case "other" -> "demo-b";
            default -> throw new IllegalArgumentException("Unknown local identity");
        };
    }
}
