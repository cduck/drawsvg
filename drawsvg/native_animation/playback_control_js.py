SVG_ONLOAD = 'svgOnLoad(event)'
SVG_JS_CONTENT = '''
/* Animation playback controls generated by drawsvg */
/* https://github.com/cduck/drawsvg/ */
function svgOnLoad(event) {
    /* Support standalone SVG or embedded in HTML or iframe */
    if (event && event.target && event.target.ownerDocument) {
        svgSetup(event.target.ownerDocument);
    } else if (document && document.currentScript
               && document.currentScript.parentElement) {
        svgSetup(document.currentScript.parentElement);
    }
}
function svgSetup(doc) {
    var svgRoot = doc.documentElement || doc;
    var scrubCapture = doc.getElementById("scrub-capture");
    /* Block multiple setups */
    if (!scrubCapture || scrubCapture.getAttribute("svgSetupDone")) {
        return;
    }
    scrubCapture.setAttribute("svgSetupDone", true);
    var scrubContainer = doc.getElementById("scrub");
    var scrubPlay = doc.getElementById("scrub-play");
    var scrubPause = doc.getElementById("scrub-pause");
    var scrubKnob = doc.getElementById("scrub-knob");
    var scrubXMin = parseFloat(scrubCapture.dataset.xmin);
    var scrubXMax = parseFloat(scrubCapture.dataset.xmax);
    var scrubTotalDur = parseFloat(scrubCapture.dataset.totaldur);
    var scrubStartDelay = parseFloat(scrubCapture.dataset.startdelay);
    var scrubEndDelay = parseFloat(scrubCapture.dataset.enddelay);
    var scrubPauseOnLoad = parseFloat(scrubCapture.dataset.pauseonload);
    var paused = false;
    var dragXOffset = 0;
    var point = svgRoot.createSVGPoint();

    function screenToSvgX(p) {
        var matrix = scrubKnob.getScreenCTM().inverse();
        point.x = p.x;
        point.y = p.y;
        return point.matrixTransform(matrix).x;
    };
    function screenToProgress(p) {
        var matrix = scrubKnob.getScreenCTM().inverse();
        point.x = p.x;
        point.y = p.y;
        var x = point.matrixTransform(matrix).x;
        if (x <= scrubXMin) {
            return scrubStartDelay / scrubTotalDur;
        }
        if (x >= scrubXMax) {
            return (scrubTotalDur - scrubEndDelay) / scrubTotalDur;
        }
        return (scrubStartDelay/scrubTotalDur
                + (x - dragXOffset - scrubXMin)
                  / (scrubXMax - scrubXMin)
                  * (scrubTotalDur - scrubStartDelay - scrubEndDelay)
                  / scrubTotalDur);
    };
    function currentScrubX() {
        return scrubKnob.cx.animVal.value;
    };
    function pause() {
        svgRoot.pauseAnimations();
        scrubPlay.setAttribute("visibility", "visible");
        scrubPause.setAttribute("visibility", "hidden");
        paused = true;
    };
    function play() {
        svgRoot.unpauseAnimations();
        scrubPause.setAttribute("visibility", "visible");
        scrubPlay.setAttribute("visibility", "hidden");
        paused = false;
    };
    function scrub(playbackFraction) {
        var t = scrubTotalDur * playbackFraction;
        /* Stop 10ms before end to avoid loop (>=1ms needed on FF) */
        var limit = scrubTotalDur - 10e-3;
        if (t < 0) t = 0;
        else if (t > limit) t = limit;
        svgRoot.setCurrentTime(t);
    };
    function mousedown(e) {
        svgRoot.pauseAnimations();
        if (e.target == scrubKnob) {
            dragXOffset = screenToSvgX(e) - currentScrubX();
        } else {
            dragXOffset = 0;
        }
        scrub(screenToProgress(e));
        /* Global document listeners */
        document.addEventListener('mousemove', mousemove);
        document.addEventListener('mouseup', mouseup);
        e.preventDefault();
    };
    function mouseup(e) {
        dragXOffset = 0;
        document.removeEventListener('mousemove', mousemove);
        document.removeEventListener('mouseup', mouseup);
        if (!paused) {
            svgRoot.unpauseAnimations();
        }
        e.preventDefault();
    };
    function mousemove(e) {
        scrub(screenToProgress(e));
    };
    scrubPause.addEventListener("click", pause);
    scrubPlay.addEventListener("click", play);
    scrubCapture.addEventListener("mousedown", mousedown);
    scrubContainer.setAttribute("visibility", "visible");
    scrubKnob.setAttribute("visibility", "visible");
    if (scrubPauseOnLoad) {
        pause();
        scrub(0);
    } else {
        play();
    }
};
svgOnLoad();
'''
