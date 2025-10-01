from typing import List

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

class Solution:
    def combinationSum4(self, nums: List[int], target: int) -> int:
        nums.sort()
        memo = { 0 : 1 }

        def dfs(total):
            if total in memo:
                return memo[total]

            res = 0
            for num in nums:
                if total < num:
                    break
                res += dfs(total - num)
            memo[total] = res
            return res

        return dfs(target)
    
if __name__ == "__main__":
    solution = Solution()
    print(solution.combinationSum4(config.C1_ARG[0], int(config.C1_ARG[1])))