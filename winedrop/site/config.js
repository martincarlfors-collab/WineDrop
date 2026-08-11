// Klientkonfiguration för push-notiser.
// Fyll i när du satt upp push-servern (se push_server/README).
// Lämna publicKey tom för att dölja notis-knappen helt.
window.WD_PUSH = {
  publicKey: "",                       // din VAPID public key (base64url)
  subscribeUrl: "",                    // t.ex. https://din-server.example/subscribe
};
