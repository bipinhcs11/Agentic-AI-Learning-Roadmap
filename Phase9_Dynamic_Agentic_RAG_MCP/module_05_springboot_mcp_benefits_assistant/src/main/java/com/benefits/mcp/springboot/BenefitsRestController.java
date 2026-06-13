package com.benefits.mcp.springboot;

import java.util.List;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.benefits.mcp.springboot.BenefitsModels.DocumentExcerpt;
import com.benefits.mcp.springboot.BenefitsModels.DocumentSummary;
import com.benefits.mcp.springboot.BenefitsModels.EmployeeProfile;
import com.benefits.mcp.springboot.BenefitsModels.HsaTaxSavingsEstimate;
import com.benefits.mcp.springboot.BenefitsModels.MatchEstimate;
import com.benefits.mcp.springboot.BenefitsModels.MatchRequest;
import com.benefits.mcp.springboot.BenefitsModels.Plan401k;
import com.benefits.mcp.springboot.BenefitsModels.PlanHsa;
import com.benefits.mcp.springboot.BenefitsModels.SearchHit;
import com.benefits.mcp.springboot.BenefitsModels.SourceCatalog;

@RestController
@RequestMapping("/api/benefits")
public class BenefitsRestController {

    private final BenefitsDataService benefitsData;
    private final RagDocumentService ragDocuments;

    public BenefitsRestController(BenefitsDataService benefitsData, RagDocumentService ragDocuments) {
        this.benefitsData = benefitsData;
        this.ragDocuments = ragDocuments;
    }

    @GetMapping("/profile")
    public EmployeeProfile profile() {
        return benefitsData.employeeProfile();
    }

    @GetMapping("/401k")
    public Plan401k plan401k() {
        return benefitsData.plan401k();
    }

    @PostMapping("/401k/match")
    public MatchEstimate calculateMatch(@RequestBody(required = false) MatchRequest request) {
        MatchRequest safeRequest = request == null ? new MatchRequest(null, null) : request;
        return benefitsData.calculate401kMatch(safeRequest.salary(), safeRequest.employeeContributionPercent());
    }

    @GetMapping("/hsa")
    public PlanHsa planHsa() {
        return benefitsData.planHsa();
    }

    @GetMapping("/hsa/tax-savings")
    public HsaTaxSavingsEstimate hsaTaxSavings(
            @RequestParam(required = false) Double annualContribution,
            @RequestParam(required = false) Double marginalTaxRate) {
        return benefitsData.estimateHsaTaxSavings(annualContribution, marginalTaxRate);
    }

    @GetMapping("/rag/search")
    public List<SearchHit> search(@RequestParam String query, @RequestParam(required = false) Integer k) {
        return ragDocuments.search(query, k);
    }

    @GetMapping("/documents")
    public List<DocumentSummary> documents() {
        return ragDocuments.listDocuments();
    }

    @GetMapping("/documents/excerpt")
    public DocumentExcerpt documentExcerpt(
            @RequestParam String documentId,
            @RequestParam(required = false) Integer maxChars) {
        return ragDocuments.getDocumentExcerpt(documentId, maxChars);
    }

    @GetMapping("/sources")
    public SourceCatalog sources() {
        return benefitsData.sources();
    }
}
