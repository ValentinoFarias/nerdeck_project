// Transition overlay animations using GSAP
// Exposes functions on window.nerdeckTransition
// Requires GSAP loaded globally (e.g. via CDN) before this script.

(function (window, document) {
  // Early: check if we should run a reveal on this page.
  // If so, mark <html> so CSS can show the overlay before any
  // content is painted. This does not depend on GSAP.
  try {
    if (window.sessionStorage && window.sessionStorage.getItem('runRevealOnNextPage') === '1') {
      document.documentElement.classList.add('run-reveal');
      window.sessionStorage.removeItem('runRevealOnNextPage');
    }
  } catch (e) {
    // Ignore storage errors; transition will just not run cross-page.
  }

  if (!window.gsap) {
    console.warn('GSAP (window.gsap) not found. Transition animations will be disabled.');
    return;
  }

  const gsap = window.gsap;

  function revealTransition() {
    return new Promise((resolve) => {
      const tl = gsap.timeline({
        onComplete: resolve,
      });

      tl.fromTo(
        '.row-1 .block',
        { scaleY: 1 },
        {
          scaleY: 0,
          duration: 1,
          delay: 0.2,
          stagger: {
            each: 0.1,
            from: 'start',
            grid: [1, 5],
            axis: 'x',
          },
          ease: 'expo.inOut',
        },
        0
      );

      tl.fromTo(
        '.row-2 .block',
        { scaleY: 1 },
        {
          scaleY: 0,
          duration: 1,
          delay: 0.2,
          stagger: {
            each: 0.1,
            from: 'start',
            grid: [1, 5],
            axis: 'x',
          },
          ease: 'expo.inOut',
        },
        0
      );
    });
  }

  function animateTransition() {
    return new Promise((resolve) => {
      gsap.set('.block', {
        visibility: 'visible',
        scaleY: 0,
      });

      const tl = gsap.timeline({
        onComplete: resolve,
      });

      tl.fromTo(
        '.row-1 .block',
        { scaleY: 0 },
        {
          scaleY: 1,
          duration: 1.4,
          delay: 0.2,
          stagger: {
            each: 0.1,
            from: 'end',
            grid: [1, 5],
            axis: 'x',
          },
          ease: 'expo.out',
        },
        0
      );

      tl.fromTo(
        '.row-2 .block',
        { scaleY: 0 },
        {
          scaleY: 1,
          duration: 1.1,
          delay: 0.2,
          stagger: {
            each: 0.1,
            from: 'end',
            grid: [1, 5],
            axis: 'x',
          },
          ease: 'expo.out',
        },
        0
      );
    });
  }

  function setupInitialRevealIfNeeded() {
    // Only run the opening reveal on the home page and
    // only when the cross-page flag/class is present.
    var path = window.location.pathname || '';
    if (path.endsWith('/home/') && document.body.classList.contains('run-reveal')) {
      gsap.set('.block', {
        visibility: 'visible',
        scaleY: 1,
      });

      revealTransition().then(() => {
        gsap.set('.block', { visibility: 'hidden' });
        document.body.classList.remove('run-reveal');
      });
    }
  }

  // Expose API globally
  window.nerdeckTransition = {
    revealTransition,
    animateTransition,
    setupInitialRevealIfNeeded,
  };

  // Automatically run initial reveal on DOM ready.
  // If the early inline script added the class on <html>, move it to <body>
  // so our existing logic keeps working.
  document.addEventListener('DOMContentLoaded', function () {
    var root = document.documentElement;
    if (root.classList.contains('run-reveal')) {
      document.body.classList.add('run-reveal');
      root.classList.remove('run-reveal');
    }

    setupInitialRevealIfNeeded();
  });
})(window, document);
