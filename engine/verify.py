def verify_fixes(before_audit, after_audit):

    before_issues = len(before_audit.get("issues", []))
    after_issues = len(after_audit.get("issues", []))

    improvement = before_issues - after_issues

    return {
        "issues_before": before_issues,
        "issues_after": after_issues,
        "improvement": improvement
    }
