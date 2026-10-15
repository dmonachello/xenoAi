# Generated sphere acceptance

## Application result

XenoDream opened the generated project and rendered Sphere2. The user then
saved `m4_generated_sphere_resaved.xxp`.

The initial generated file had 3,465 bytes. The resaved file has 3,400 bytes.
One value changed:

```text
SelectionSpots.0
before: 3 25 1 2 3 ... 25
after:  3 1 1
```

No geometry, transform, metamorph, camera, material, or lighting value
changed. The meaning of `SelectionSpots` remains unknown.

The compiler now uses the resaved 3,400-byte file as its opaque sphere
template. The current default output has SHA-256
`19bdf9608585ea50de30490d08ac0ae80aa96803d6de6028191559ba314f9013`.

Application status: accepted. XenoDream opened and rendered the generated
sphere. The first resave normalized one opaque selection record.
