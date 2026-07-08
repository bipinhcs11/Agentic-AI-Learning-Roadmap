package com.benefits.adk.ucp;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

// A fictional benefits plan a category is eligible for. This is the UCP
// "catalog" entry: it declares the employer-match tiers and the savings account employer
// seed so the transaction lane can compute employer contributions.
public record BenefitsPlanOption(
        EmployeeCategory category,
        String planName,
        List<MatchTier> matchTiers,
        BigDecimal savingsEmployerSeedSelfOnly,
        BigDecimal savingsEmployerSeedFamily
) {
    // One employer-match band: match `rate` on employee deferral percent up to
    // `upToPercent` (measured from the previous tier's ceiling).
    public record MatchTier(BigDecimal upToPercent, BigDecimal rate) {
    }

    public BenefitsPlanOption {
        matchTiers = matchTiers == null ? List.of() : List.copyOf(matchTiers);
    }

    // Deterministic tiered match. e.g. standard = 100% of first 3% + 50% of
    // next 3%; a 6% deferral on $90k pay -> $2,700 + $1,350 = $4,050.
    public BigDecimal employerMatch(BigDecimal annualSalary, BigDecimal employeePrimaryPercent) {
        BigDecimal salary = annualSalary == null ? BigDecimal.ZERO : annualSalary;
        BigDecimal percent = employeePrimaryPercent == null ? BigDecimal.ZERO : employeePrimaryPercent;
        BigDecimal match = BigDecimal.ZERO;
        BigDecimal previousCeiling = BigDecimal.ZERO;
        for (MatchTier tier : matchTiers) {
            BigDecimal eligiblePercentInTier = percent.min(tier.upToPercent()).subtract(previousCeiling).max(BigDecimal.ZERO);
            BigDecimal tierMatch = salary
                    .multiply(eligiblePercentInTier)
                    .divide(new BigDecimal("100"), 8, RoundingMode.HALF_UP)
                    .multiply(tier.rate());
            match = match.add(tierMatch);
            previousCeiling = tier.upToPercent();
        }
        return match.setScale(2, RoundingMode.HALF_UP);
    }

    public BigDecimal savingsEmployerSeed(boolean familyCoverage) {
        BigDecimal seed = familyCoverage ? savingsEmployerSeedFamily : savingsEmployerSeedSelfOnly;
        return (seed == null ? BigDecimal.ZERO : seed).setScale(2, RoundingMode.HALF_UP);
    }

    // Plain-language summary of the match, for A2UI text and receipts.
    public String matchDescription() {
        if (matchTiers.isEmpty()) {
            return "No employer match.";
        }
        StringBuilder builder = new StringBuilder();
        BigDecimal previousCeiling = BigDecimal.ZERO;
        for (int index = 0; index < matchTiers.size(); index++) {
            MatchTier tier = matchTiers.get(index);
            BigDecimal band = tier.upToPercent().subtract(previousCeiling);
            int ratePercent = tier.rate().multiply(new BigDecimal("100")).intValue();
            if (index > 0) {
                builder.append(" plus ");
            }
            builder.append(ratePercent).append("% of ")
                    .append(index == 0 ? "the first " : "the next ")
                    .append(band.stripTrailingZeros().toPlainString()).append("% of pay");
            previousCeiling = tier.upToPercent();
        }
        return builder.append(".").toString();
    }
}
