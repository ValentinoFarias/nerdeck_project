document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("heroVideo");
  const playButton = document.getElementById("overlayPlayHeroVideo");
  const pauseButton = document.getElementById("pauseHeroVideo");

  if (!video || !playButton || !pauseButton) return;

  playButton.addEventListener("click", () => {
    video.play();
    playButton.classList.add("d-none");
	pauseButton.classList.remove("pause-hidden");
  });

  pauseButton.addEventListener("click", () => {
    video.pause();
  });

	video.addEventListener("ended", () => {
    pauseButton.classList.add("pause-hidden");
		playButton.classList.remove("d-none");
	});
});
