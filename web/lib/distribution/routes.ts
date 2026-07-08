/** Canonical Settings deep-link for distribution hub (connections + publish queue). */
export const DISTRIBUTION_SETTINGS_HREF = "/settings?section=distribution";

export const DISTRIBUTION_LOGIN_NEXT = `/login?next=${encodeURIComponent(DISTRIBUTION_SETTINGS_HREF)}`;
