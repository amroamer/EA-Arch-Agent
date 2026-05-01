/**
 * Feature flags. Flip a single boolean to hide a feature across the app
 * without ripping out routes or backend endpoints.
 *
 * The Compare feature is currently hidden in the UI. The /compare API
 * endpoint, page route, and existing compare sessions in the database
 * are left intact so the feature can be re-enabled by flipping
 * COMPARE_ENABLED back to true.
 */
export const COMPARE_ENABLED = false;
