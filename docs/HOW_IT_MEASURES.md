# How Galileo Blink measures, and what it cannot

Everything on screen is produced by the steps below. The main tuning numbers live in
[`galileo_blink/engine/constants.py`](../galileo_blink/engine/constants.py), each with its
reason. Numbers that belong to one step are named at the top of that step's module.

## 1. Getting the photos

1. **Which photos cover the place.** IRSA's Simple Image Access service is asked, per data
   collection, for every SPHEREx Level-2 exposure containing the position. All six cameras.
2. **Looks and seasons.** One camera's photos separated by more than 30 days are different
   *looks*. Cameras do not look on the same days, so looks whose middle dates fall within 45
   days are shown together as one *season*. Near the ecliptic poles coverage never stops; there
   a season is a calendar month.
3. **Cutouts.** Up to four photos per camera per season (six for the prebuilt targets) are
   read as cutouts directly from NASA's public cloud copy of the archive, with IRSA's own copy
   as fallback. A cutout is 1.45 times wider than the view, because photos arrive rolled.

## 2. Making the pictures

1. **Mask.** Pixels flagged SUR_ERROR, NONFUNC, MISSING_DATA, HOT or COLD become "no data".
   Nothing else is masked. In particular OUTLIER, BLOOM, HALO, SNOWBALL and SATELLITE_HALO are
   kept, because NASA's pipeline sets them on real moving objects, and NONLINEAR is kept
   because it marks every bright star.
2. **Align.** Each photo is resampled (bilinear) onto one grid: north up, east left, 6.15″
   pixels. Photos with a FINAST astrometry grade other than 0 ("good") are not used.
3. **Stack.** Each photo's own median (the zodiacal glow) is removed, then photos of one look
   are combined: the median of three or more; for two, the mean unless they disagree by more
   than noise and wavelength can explain, in which case the fainter value (a cosmic ray only
   adds light).
4. **Display.** One brightness scale per camera, shared by all its seasons: black at the sky's
   median plus two sigma, an asinh stretch above. "No data" is transparent and drawn hatched.
5. **Change maps.** One date minus another, after scaling so the field's stars match, divided
   by a noise that grows under bright stars (their brightness differs between photos because
   each photo is a different wavelength).

## 3. Where catalogued objects should be

Gaia DR3 (from NASA MAST) and CatWISE2020 (from IRSA) give a position at an epoch, a proper
motion and, for Gaia, a parallax. The position on any date is

    position(epoch) + proper motion x years + parallax x Earth's displacement

with Earth's position from Astropy's built-in ephemeris. Gaia stars moving at least 0.5″ per
year are marked. CatWISE objects are marked only if they move at least 2″ per year and that
motion is at least 5 times its own error; slower CatWISE motions are mostly blends in crowded
fields. A place typed by name, or by an old catalogue position, is followed to where
the object is today (NASA's WISE 0855 coordinate is its 2010 position, 2 arcminutes away).

## 4. Measuring motion

1. **In native pixels.** The star is measured in each photo's own pixels, never in the
   resampled picture.
2. **Profile fit.** SPHEREx's star image is 1.2 to 1.5 pixels wide. The position is the centre
   of a Gaussian of the photo's own width (`PSF_FWHM`), *integrated over each pixel*, fitted to
   the unmasked pixels within 3.5 pixels. A masked pixel within 1.5 pixels makes the brightness
   unusable but not the position.
3. **Saturated stars.** With three or more masked core pixels the brightness is not measured.
   The position comes from fitting the unsaturated wings out to 6.5 pixels with a profile twice
   as wide. Checked on Barnard's Star: 110 saturated photos in six cameras gave positions
   within 0.1 to 0.4″ of Gaia's prediction in the median, with 0.5 to 1.3″ scatter per photo.
4. **Registration.** Each photo's sky mapping is off by about an arcsecond. Up to eight
   isolated Gaia stars (G 9.5 to 17) in the same photo are measured the same way; the median of
   their offsets from Gaia is that photo's error, and is subtracted.
5. **Per look.** A look's position is the median over its photos. With three or more photos
   its error is the scatter between them, never less than 0.3″ divided by the square root of
   the number of photos. With one or two photos there is no scatter to measure, so the error
   is a per-photo floor (0.3″ clean, 0.6″ partly masked, 1.0″ saturated, or more for a faint
   object) divided by the square root of the number of photos. The photo's registration error
   is then added.
6. **Motion.** Between two looks, measured displacement = predicted displacement + change in
   (measured minus predicted). Looks a whole number of years apart are preferred, because
   parallax then cancels. Motion is compared with the catalogue **as a vector**: a star that
   moved the right distance in the wrong direction does not "agree". The measurement agrees
   when the difference between the measured and predicted vectors is within 2.45 per-axis
   errors (`constants.AGREE_FACTOR`); a true match falls inside that distance 95 percent of
   the time in two dimensions.
7. **The honesty floor.** The same reference stars do not move, yet after all corrections they
   still appear to shift a little between looks. That scatter is added to the error. Typical
   value: 0.2 to 0.4″.
8. **Guards.** A camera's look counts only if the object is detected there (median signal to
   noise 5 or more) and sits within 3″ of its predicted path; otherwise what is being measured
   is a different, usually static, object.
9. **Several cameras.** Cameras that compared the same two seasons are averaged, weighted by
   their errors.
10. **What averaging cannot remove.** The cameras share the same pointing errors and the same
    star, so they are not fully independent. For seven stars with well-known motions the
    all-camera result differed from the catalogue by 0.3 to 0.7″ (1.3″ for R Draconis, which
    is saturated in every photo), more than the scatter explains, so 0.3″ is added to every
    motion's error. That allowance was set using these same stars, so the results table in
    the README shows that the numbers are consistent, not an independent test of the error
    bars.

## 5. Spectra

- **From the view's photos.** Each photo sees the object at a different wavelength. The fitted
  brightness of every clean photo is plotted against its wavelength, coloured by season.
  Saturated and partly masked photos are counted but not plotted as brightness. A confident
  detection more than 3″ from the predicted path is a neighbour's light and is left out.
- **Quick look anywhere.** The DR1 all-sky cube gives all 102 channels at any position:
  brightness in the central 3 x 3 pixels (38.6″) above the surrounding 7 x 7 ring. It averages
  all dates and has 12.9″ pixels, so it shows the shape of a spectrum, not precise brightness
  or change.

## 6. Asteroids (one visit)

Within one visit (up to 10 days, one camera) photos taken within 29 minutes form a *moment*.
The median of the moments is the sky that stays put; each moment minus that sky leaves what was
different then. Leftovers of 5 sigma or more are linked into straight, steady paths: at least
three moments and at most 0.8 pixel scatter, and the two sightings that start a path must be
at least 1.5 pixels apart. A path seen in only three moments must reach 6 sigma in each.
A path is **strong** if seen in four or more moments and in 70% of those where it could have
been seen, or if a catalogued asteroid (IMCCE SkyBoT) is predicted on it in two moments;
otherwise it is **possible**. Movers are searched for only where three moments overlap.

## 7. What it cannot do

| Limit | Why |
|---|---|
| Motion smaller than about 1″ between looks (2 to 3″ in one camera, or for faint or saturated objects) cannot be told apart from no motion | SPHEREx pixels are 6.15″; with all cameras the error is 0.39 to 0.46″ and "agrees" allows 2.45 errors; stars that do not move still appear to shift 0.2 to 0.4″ |
| The brightness of saturated stars is not measured | Their cores are lost; R Draconis is saturated in every photo |
| A brightness change needs care | Every photo is at a different wavelength; compare dots at the same wavelength |
| A moving object passing a static one is blended | WISE 0855 passes 4″ from a faint star that does not move in May 2026. The blend stays inside the 3″ track guard, so camera 5's May 2026 position is pulled about 1″ toward that star; this is why it reads 9.0″ against a predicted 8.1″ |
| CatWISE movers near a bright star are not marked | Within 4 arcminutes of a star brighter than Gaia magnitude 10.5, its glare and spikes create false CatWISE movers, so none are marked there; a real faint mover that close would be missed |
| An asteroid in view for fewer than three moments cannot be found | Three sightings are the minimum for a path, at any brightness |
| Three aligned leftovers can be chance | Cosmic-ray hits line up; such paths are labelled "possible" |
| Asteroids fainter than about V 18.5 are not expected to be found | Single SPHEREx photos are not deep enough |
| It cannot find a distant planet | One would be fainter than a single photo shows, and would jump 10 to 25 arcminutes between looks |
