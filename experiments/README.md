# Controlled XenoDream experiment

Please create two minimal XenoDream X projects that differ by one UI setting.
The first experiment should test X scale without guessing where that value is
stored in the file.

1. Record the exact XenoDream X version shown in Help > About.
2. Start a new project and add one sphere constructor inside the default group.
3. Leave every displayed setting at its default. Save as
   `sphere_base.xxp`.
4. Change only the sphere's X Scale control. Record the displayed before and
   after values. Do not move the object or change the camera.
5. Save as `sphere_x_scale.xxp`. Do not overwrite the base file.
6. Close and reopen both files in XenoDream X. Confirm whether each opens and
   renders, and note any warning or visible difference.
7. Copy both files into `experiments/scale-x/`, together with a short
   `notes.txt` containing the version, exact UI action, values, and open/render
   results. Screenshots are useful but optional.

Do not hand-edit either `.xxp` file. File timestamps and names can differ. The
structural diff will identify every content change, including any extra values
that XenoDream updates while saving. If the save changes unrelated data, the
next experiment will add a no-change Save As control before drawing semantic
conclusions.

