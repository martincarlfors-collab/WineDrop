# WineDrop som native-app (Capacitor)

Capacitor paketerar exakt samma PWA (`site/`) till en iOS- och Android-app utan
att skriva om något. Datalagret (JSON-API) är oförändrat.

## Förutsättningar

- Node 18+, npm
- iOS: macOS + Xcode
- Android: Android Studio + JDK 17

## Kom igång

```bash
cd winedrop
npm install
npx cap init WineDrop se.niti.winedrop --web-dir=site   # redan konfigurerat i capacitor.config.json

# Lägg till plattformar
npm run cap:add:ios
npm run cap:add:android

# Efter varje ändring i site/: synka in webbfilerna i native-projekten
npm run cap:sync

# Kör
npm run cap:ios       # öppnar/köra i Xcode-simulator
npm run cap:android   # öppnar/köra i Android-emulator
```

## Uppdatera innehåll

Appen laddar `site/`-filerna som är inbakade i appen. Själva **datan** hämtas
live från ditt JSON-API (GitHub Pages/CDN), så nya vinsläpp syns direkt utan att
släppa en ny app-version. Endast ändringar i UI-koden kräver `cap sync` + ny build.

## Push på native

Webben använder Web Push (redan byggt). På native rekommenderas Capacitors
`@capacitor/push-notifications` som går via APNs (iOS) och FCM (Android):

1. Skapa Firebase-projekt (Android) och aktivera Push i Apple Developer (iOS).
2. Lägg `GoogleService-Info.plist` / `google-services.json` i respektive projekt.
3. I appstarten: registrera token och skicka den till din push-server (samma
   `/subscribe`-endpoint, men lagra `fcm_token` istället för web-push-subscription).
4. `notify.py` kan då skicka via FCM/APNs för native och Web Push för webben.

För en första version fungerar Web Push även i den native-wrappade appen på
Android; iOS kräver APNs-vägen ovan.

## Ikoner & splash

```bash
npm i -D @capacitor/assets
npx capacitor-assets generate   # använder site/icon.svg som källa
```

## Publicering

- **iOS:** Xcode → Archive → App Store Connect.
- **Android:** Android Studio → Generate Signed Bundle → Google Play Console.
