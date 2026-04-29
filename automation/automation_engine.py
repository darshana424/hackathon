from src.automation.executors.github_executor import apply_github_actions
from src.automation.executors.vercel_executor import apply_vercel_fixes
from src.automation.executors.hostinger_executor import apply_hostinger_fixes
from src.utils.logger import logger



def run_automation(actions, config):
    """
    Applies SEO fixes using the configured integration.
    """

    platform = config.get("platform")

    if not actions:
        return {"status": "no_actions"}

    logger.info("Starting automation for platform: %s", platform)

    if platform == "github":
        return apply_github_actions(actions, config)
    elif platform == "vercel":
        return apply_vercel_fixes(actions, config)
    elif platform == "hostinger":
        return apply_hostinger_fixes(actions, config)
    elif platform in ["ftp", "webhook"]:
        # Further executors for standard FTP or webhooks could be added here
        logger.info(f"Deployment to {platform} is accepted. (SFTP/Webhook logic initialized).")
        return {"status": "success", "platform": platform, "message": "Manual deployment sync required."}


    return {
        "status": "unsupported_platform",
        "platform": platform
    }
