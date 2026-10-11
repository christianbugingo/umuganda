const sceneElement = document.querySelector('[data-home-motion-scene]');

if (sceneElement) {
    const canvas = sceneElement.querySelector('.home-motion-canvas');
    const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');

    import('https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js')
        .then((THREE) => createScene(THREE))
        .catch(() => sceneElement.classList.add('is-fallback'));

    function createScene(THREE) {
        let renderer;

        try {
            renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
            renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
            renderer.setClearColor(0x000000, 0);
        } catch {
            sceneElement.classList.add('is-fallback');
            return;
        }

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 50);
        camera.position.set(0, 0, 8.2);
        scene.add(new THREE.AmbientLight(0xffffff, 1.7));

        const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
        keyLight.position.set(-3, 5, 7);
        scene.add(keyLight);

        const rimLight = new THREE.DirectionalLight(0xf4b779, 1.4);
        rimLight.position.set(4, -2, 3);
        scene.add(rimLight);

        const badges = [
            createBadge(THREE, 'COMMUNITY', 'ROOTED IN EVERY NEIGHBORHOOD', '#236b48', 2.15, 1.22),
            createBadge(THREE, 'TOGETHER', 'ONE SHARED PURPOSE', '#bd6337', 1.85, 1.1),
            createBadge(THREE, 'RWANDA', 'LOCAL ACTION, LASTING CHANGE', '#235f78', 2.05, 1.18),
        ];

        const placements = [
            { x: -1.72, y: 0.2, z: 0, tilt: -0.14, phase: 0 },
            { x: 0, y: -0.32, z: 0.2, tilt: 0.1, phase: 2.1 },
            { x: 1.72, y: 0.22, z: -0.15, tilt: -0.07, phase: 4.2 },
        ];
        let sceneVisible = true;
        let pendingFrame = null;

        badges.forEach((badge, index) => {
            const placement = placements[index];
            badge.position.set(placement.x, placement.y, placement.z);
            badge.rotation.z = placement.tilt;
            badge.userData = placement;
            scene.add(badge);
        });

        function resizeScene() {
            const bounds = canvas.getBoundingClientRect();
            if (!bounds.width || !bounds.height) return;
            renderer.setSize(Math.round(bounds.width), Math.round(bounds.height), false);
            camera.aspect = bounds.width / bounds.height;
            camera.updateProjectionMatrix();
            scheduleRender();
        }

        function scheduleRender() {
            if (!sceneVisible || pendingFrame !== null) return;
            pendingFrame = window.requestAnimationFrame(() => {
                pendingFrame = null;
                renderScene();
            });
        }

        function renderScene() {
            if (!motionPreference.matches) {
                const bounds = sceneElement.getBoundingClientRect();
                const progress = THREE.MathUtils.clamp(
                    (window.innerHeight - bounds.top) / (window.innerHeight + bounds.height),
                    0,
                    1,
                );

                badges.forEach((badge) => {
                    const { x, y, z, tilt, phase } = badge.userData;
                    badge.rotation.x = Math.sin(progress * Math.PI * 2 + phase) * 0.12;
                    badge.rotation.y = (progress - 0.5) * 0.75;
                    badge.rotation.z = tilt + Math.sin(progress * Math.PI * 2 + phase) * 0.045;
                    badge.position.set(
                        x + Math.cos(progress * Math.PI * 2 + phase) * 0.08,
                        y + Math.sin(progress * Math.PI * 2 + phase) * 0.14,
                        z,
                    );
                });
            }

            renderer.render(scene, camera);
        }

        function roundedRectangle(width, height, radius) {
            const shape = new THREE.Shape();
            shape.moveTo(-width / 2 + radius, -height / 2);
            shape.lineTo(width / 2 - radius, -height / 2);
            shape.quadraticCurveTo(width / 2, -height / 2, width / 2, -height / 2 + radius);
            shape.lineTo(width / 2, height / 2 - radius);
            shape.quadraticCurveTo(width / 2, height / 2, width / 2 - radius, height / 2);
            shape.lineTo(-width / 2 + radius, height / 2);
            shape.quadraticCurveTo(-width / 2, height / 2, -width / 2, height / 2 - radius);
            shape.lineTo(-width / 2, -height / 2 + radius);
            shape.quadraticCurveTo(-width / 2, -height / 2, -width / 2 + radius, -height / 2);
            return shape;
        }

        function createBadgeTexture(label, caption, color) {
            const face = document.createElement('canvas');
            face.width = 768;
            face.height = 384;
            const context = face.getContext('2d');
            context.fillStyle = color;
            context.beginPath();
            context.roundRect(10, 10, 748, 364, 54);
            context.fill();

            context.strokeStyle = '#fff5df';
            context.lineWidth = 11;
            context.lineCap = 'round';
            context.lineJoin = 'round';
            context.beginPath();
            context.moveTo(100, 270);
            context.bezierCurveTo(106, 220, 118, 174, 164, 112);
            context.moveTo(118, 204);
            context.bezierCurveTo(75, 196, 67, 151, 76, 132);
            context.bezierCurveTo(120, 133, 143, 156, 118, 204);
            context.moveTo(132, 174);
            context.bezierCurveTo(137, 130, 168, 105, 203, 103);
            context.bezierCurveTo(206, 149, 181, 171, 132, 174);
            context.stroke();

            context.fillStyle = '#fffaf0';
            context.textAlign = 'left';
            context.textBaseline = 'middle';
            context.font = '700 52px system-ui, sans-serif';
            context.fillText(label, 238, 168, 485);
            context.globalAlpha = 0.83;
            context.font = '600 22px system-ui, sans-serif';
            context.fillText(caption, 242, 224, 470);
            context.globalAlpha = 1;

            const texture = new THREE.CanvasTexture(face);
            texture.colorSpace = THREE.SRGBColorSpace;
            return texture;
        }

        function createBadge(THREE, label, caption, color, width, height) {
            const shape = roundedRectangle(width, height, 0.28);
            const geometry = new THREE.ExtrudeGeometry(shape, {
                depth: 0.14,
                bevelEnabled: true,
                bevelSegments: 4,
                bevelSize: 0.055,
                bevelThickness: 0.045,
            });
            geometry.computeVertexNormals();

            const badge = new THREE.Group();
            const backing = new THREE.Mesh(
                geometry,
                new THREE.MeshStandardMaterial({ color: 0xfff7e7, roughness: 0.38 }),
            );
            backing.castShadow = true;
            backing.receiveShadow = true;
            badge.add(backing);

            const face = new THREE.Mesh(
                new THREE.PlaneGeometry(width * 0.88, height * 0.82),
                new THREE.MeshBasicMaterial({
                    map: createBadgeTexture(label, caption, color),
                    transparent: true,
                    side: THREE.DoubleSide,
                    toneMapped: false,
                }),
            );
            face.position.z = 0.205;
            badge.add(face);
            return badge;
        }

        const resizeObserver = new ResizeObserver(resizeScene);
        resizeObserver.observe(sceneElement);
        if ('IntersectionObserver' in window) {
            sceneVisible = false;
            const visibilityObserver = new IntersectionObserver((entries) => {
                sceneVisible = entries.some((entry) => entry.isIntersecting);
                if (sceneVisible) scheduleRender();
            });
            visibilityObserver.observe(sceneElement);
        }
        window.addEventListener('scroll', scheduleRender, { passive: true });
        motionPreference.addEventListener('change', scheduleRender);
        resizeScene();
    }
}