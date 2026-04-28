export function setupAntiGravity() {
  // Intentionally disabled in the current UI to keep the experience focused.
  return {
    enabled: false,
    enable: () => false,
    disable: () => false
  };
}
