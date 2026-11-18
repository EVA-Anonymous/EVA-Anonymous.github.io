(() => {
  "use strict";

  const config = window.EVA_CONFIG || {};
  const icons = () => window.lucide?.createIcons();
  const safeUrl = (value) => {
    if (typeof value !== "string" || !value.trim()) return null;
    try {
      const url = new URL(value, document.baseURI);
      return ["https:", "http:"].includes(url.protocol) ? url.href : null;
    } catch { return null; }
  };

  const canonicalUrl = safeUrl(config.canonicalUrl);
  if (canonicalUrl) {
    const canonical = document.createElement("link");
    canonical.rel = "canonical";
    canonical.href = canonicalUrl;
    document.head.append(canonical);
    const ogUrl = document.createElement("meta");
    ogUrl.setAttribute("property", "og:url");
    ogUrl.content = canonicalUrl;
    document.head.append(ogUrl);
    const base = canonicalUrl.endsWith("/") ? canonicalUrl : `${canonicalUrl}/`;
    document.querySelector('meta[property="og:image"]').content = new URL("assets/images/bottles.jpg", base).href;
  }

  const menuButton = document.querySelector(".menu-toggle");
  const mobileMenu = document.getElementById("mobile-nav");
  const closeMenu = () => {
    mobileMenu.hidden = true;
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", "Open navigation");
    menuButton.title = "Open navigation";
  };
  menuButton.addEventListener("click", () => {
    const open = mobileMenu.hidden;
    mobileMenu.hidden = !open;
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    menuButton.title = open ? "Close navigation" : "Open navigation";
  });
  mobileMenu.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !mobileMenu.hidden) { closeMenu(); menuButton.focus(); }
  });
  window.matchMedia("(min-width: 541px)").addEventListener("change", closeMenu);

  const demos = {
    bottles: { title: "Bottle placement", description: "A task where ordering matters: EVA plans to move the orange bottle before the white bottle to avoid an unintended collision.", speed: "Source playback" },
    memory: { title: "Three-cup task", description: "A real-world three-cup demonstration, presented with the original edited sequence and timestamps.", speed: "Mixed source speed-up" },
    box: { title: "Box transport", description: "A qualitative real-world demonstration of the humanoid interacting with and transporting a box.", speed: "8\u00d7 playback" },
    chair: { title: "Chair pushing", description: "A qualitative real-world demonstration of the humanoid pushing a chair.", speed: "8\u00d7 playback" },
  };
  const demoVideo = document.getElementById("demo-video");
  document.querySelectorAll("[data-demo]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.getAttribute("aria-pressed") === "true") return;
      const key = button.dataset.demo;
      const demo = demos[key];
      const wasPlaying = !demoVideo.paused;
      demoVideo.pause();
      demoVideo.poster = `assets/images/${key}.jpg`;
      demoVideo.querySelector("source").src = `assets/videos/${key}.mp4`;
      demoVideo.setAttribute("aria-label", `${demo.title} demonstration`);
      demoVideo.load();
      document.getElementById("demo-title").textContent = demo.title;
      document.getElementById("demo-description").textContent = demo.description;
      document.getElementById("demo-speed").textContent = demo.speed;
      document.querySelectorAll("[data-demo]").forEach((choice) => {
        const selected = choice === button;
        choice.classList.toggle("selected", selected);
        choice.setAttribute("aria-pressed", String(selected));
      });
      if (wasPlaying) demoVideo.play().catch(() => {});
    });
  });

  document.querySelectorAll('video').forEach((video) => {
    video.addEventListener('play', () => {
      document.querySelectorAll('video').forEach((other) => {
        if (other !== video) other.pause();
      });
    });
  });
  icons();
})();
