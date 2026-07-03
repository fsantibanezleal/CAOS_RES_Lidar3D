import { describe, it, expect } from 'vitest';
import {
  worldToRender,
  worldToRenderBuffer,
  poseCenter,
  poseForward,
  poseApplyToRender,
  cloudObbRender,
  obbAxes,
} from './coords';

// The `-y, -z` map produces IEEE-754 negative zero for zero inputs (harmless in WebGL, but -0 !== 0 for
// toEqual). Flush -0 to +0 so the assertions read cleanly.
const flush = (a: readonly number[]): number[] => a.map((v) => v + 0);

describe('worldToRender', () => {
  it('maps OpenCV world to the render frame as (x, -y, -z)', () => {
    expect(flush(worldToRender(1, 2, 3))).toEqual([1, -2, -3]);
    expect(flush(worldToRender(0, 0, 0))).toEqual([0, 0, 0]);
    expect(flush(worldToRender(-5, 4, -7))).toEqual([-5, -4, 7]);
  });

  it('is handedness-preserving (determinant +1, i.e. a rotation, NOT a mirror)', () => {
    // columns = images of the world basis vectors under the transform
    const c1 = worldToRender(1, 0, 0);
    const c2 = worldToRender(0, 1, 0);
    const c3 = worldToRender(0, 0, 1);
    const det =
      c1[0] * (c2[1] * c3[2] - c2[2] * c3[1]) -
      c1[1] * (c2[0] * c3[2] - c2[2] * c3[0]) +
      c1[2] * (c2[0] * c3[1] - c2[1] * c3[0]);
    expect(det).toBeCloseTo(1, 12); // +1 => no mirror; -1 would be a reflection
  });

  it('is an involution (applying it twice returns the original point)', () => {
    const [x, y, z] = worldToRender(3, -4, 5);
    expect(flush(worldToRender(x, y, z))).toEqual([3, -4, 5]);
  });
});

describe('worldToRenderBuffer', () => {
  it('matches worldToRender point by point', () => {
    const world = new Float32Array([1, 2, 3, -4, 5, -6, 0, 0, 0]);
    const out = worldToRenderBuffer(world);
    expect(out).toHaveLength(9);
    for (let i = 0; i < 3; i++) {
      const expected = worldToRender(world[i * 3], world[i * 3 + 1], world[i * 3 + 2]);
      expect(flush([out[i * 3], out[i * 3 + 1], out[i * 3 + 2]])).toEqual(flush(expected));
    }
  });

  it('applies the stride', () => {
    const world = new Float32Array([1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]);
    const out = worldToRenderBuffer(world, 2); // points 0 and 2
    expect(out).toHaveLength(6);
    expect(flush([out[0], out[1], out[2]])).toEqual([1, -1, -1]);
    expect(flush([out[3], out[4], out[5]])).toEqual([3, -3, -3]);
  });
});

describe('pose helpers', () => {
  // identity rotation, translation (2,3,5); row-major 3x4
  const pose = [1, 0, 0, 2, 0, 1, 0, 3, 0, 0, 1, 5];

  it('poseCenter is the translation, mapped to the render frame', () => {
    expect(flush(poseCenter(pose))).toEqual([2, -3, -5]);
  });

  it('poseForward is the unit +Z camera axis in the render frame', () => {
    expect(flush(poseForward(pose))).toEqual([0, 0, -1]);
  });

  it('poseForward normalises', () => {
    const scaled = [0, 0, 3, 2, 0, 0, 0, 3, 0, 0, 4, 5]; // forward column = (3,0,4), |.|=5
    const f = poseForward(scaled);
    expect(Math.hypot(f[0], f[1], f[2])).toBeCloseTo(1, 12);
    expect(flush(f)).toEqual([3 / 5, 0, -4 / 5]);
  });

  it('poseApplyToRender transforms a local point through the pose, then to the render frame', () => {
    // local (0,0,1) under identity+t=(2,3,5) -> world (2,3,6) -> render (2,-3,-6)
    expect(flush(poseApplyToRender(pose, 0, 0, 0, 1))).toEqual([2, -3, -6]);
    // local origin maps to the camera centre
    expect(flush(poseApplyToRender(pose, 0, 0, 0, 0))).toEqual(flush(poseCenter(pose)));
  });

  it('reads a pose at an arbitrary offset', () => {
    const two = [0, 0, 0, 0, /* pad */ 1, 0, 0, 9, 0, 1, 0, 8, 0, 0, 1, 7];
    expect(flush(poseCenter(two, 4))).toEqual([9, -8, -7]);
  });
});

describe('cloudObbRender', () => {
  // world points -> render: (0,0,0),(2,0,0),(0,-4,0),(0,0,-6)
  const world = new Float32Array([0, 0, 0, 2, 0, 0, 0, 4, 0, 0, 0, 6]);

  it('computes the render-frame AABB (min/max/center/size)', () => {
    const o = cloudObbRender(world);
    expect(flush(o.min)).toEqual([0, -4, -6]);
    expect(flush(o.max)).toEqual([2, 0, 0]);
    expect(flush(o.center)).toEqual([1, -2, -3]);
    expect(flush(o.size)).toEqual([2, 4, 6]);
  });

  it('returns 8 corners and 12 edges, all corners on the box', () => {
    const o = cloudObbRender(world);
    expect(o.corners).toHaveLength(8);
    expect(o.edges).toHaveLength(12);
    for (const [cx, cy, cz] of o.corners) {
      expect(cx === o.min[0] || cx === o.max[0]).toBe(true);
      expect(cy === o.min[1] || cy === o.max[1]).toBe(true);
      expect(cz === o.min[2] || cz === o.max[2]).toBe(true);
    }
    // every edge connects two corners that differ in exactly one axis (a real box edge)
    for (const [a, b] of o.edges) {
      let diff = 0;
      for (let k = 0; k < 3; k++) if (o.corners[a][k] !== o.corners[b][k]) diff++;
      expect(diff).toBe(1);
    }
  });

  it('honours the stride (subsampling still bounds the sampled points)', () => {
    const o = cloudObbRender(world, 2); // samples points 0 and 2 => render (0,0,0),(0,-4,0)
    expect(flush(o.min)).toEqual([0, -4, 0]);
    expect(flush(o.max)).toEqual([0, 0, 0]);
  });
});

describe('obbAxes', () => {
  const world = new Float32Array([0, 0, 0, 2, 0, 0, 0, 4, 0, 0, 0, 6]);

  it('places the RGB triad at the OBB min corner, pointing along +X/+Y/+Z', () => {
    const o = cloudObbRender(world);
    const ax = obbAxes(o, 0.5);
    expect(ax.origin).toEqual(o.min);
    expect(ax.len).toBeGreaterThan(0);
    // each tip differs from the origin only along its own axis, by +len
    expect(flush(ax.x)).toEqual(flush([o.min[0] + ax.len, o.min[1], o.min[2]]));
    expect(flush(ax.y)).toEqual(flush([o.min[0], o.min[1] + ax.len, o.min[2]]));
    expect(flush(ax.z)).toEqual(flush([o.min[0], o.min[1], o.min[2] + ax.len]));
  });
});
