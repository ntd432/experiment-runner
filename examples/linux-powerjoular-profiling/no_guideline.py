from typing import List

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

class Solution:
    def combinationSum4(self, nums: List[int], target: int) -> int:
        nums.sort()

        def dfs(total):
            if total == 0:
                return 1

            res = 0
            for i in range(len(nums)):
                if total < nums[i]:
                    break
                res += dfs(total - nums[i])
            return res

        return dfs(target)

if __name__ == "__main__":
    solution = Solution()
    print(solution.combinationSum4(config.C1_ARG[0], int(config.C1_ARG[1])))
